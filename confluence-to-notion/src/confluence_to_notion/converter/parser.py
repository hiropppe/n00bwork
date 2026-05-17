"""Confluence Storage Format XML → ConversionNode（中間表現）"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag, NavigableString

from .mappings import normalize_language, COLOR_MAP, EMOJI_MAP, UNSUPPORTED_MACROS

_AC_NS = "http://www.atlassian.com/schema/confluence/4/ac/"
_RI_NS = "http://www.atlassian.com/schema/confluence/4/ri/"

# lxml-xml パーサーは名前空間を展開して ac: プレフィックスをタグ名から除去する。
# lxml（HTMLパーサー）は ac:structured-macro のままタグ名を保持するため、こちらを使う。
_PARSER = "lxml"

_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


def _preprocess_cdata(xml: str) -> str:
    """lxml HTML パーサーが無視する CDATA セクションをエスケープ済みテキストに変換する"""
    def _escape(m: re.Match) -> str:
        return m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _CDATA_RE.sub(_escape, xml)


@dataclass
class ConversionNode:
    node_type: str
    rich_text: list[dict] = field(default_factory=list)
    children: list["ConversionNode"] = field(default_factory=list)
    attrs: dict = field(default_factory=dict)


def parse_storage_xml(xml: str) -> list[ConversionNode]:
    """Storage Format XML 文字列を ConversionNode リストに変換する"""
    soup = BeautifulSoup(_preprocess_cdata(xml), _PARSER)
    # lxml HTML パーサーは <html><body> でラップするため <root> を明示的に探す
    root = soup.find("root")
    if root is None:
        root = soup.find("body")
    if root is None:
        return []
    return _parse_children(root)


def _parse_children(parent: Tag) -> list[ConversionNode]:
    nodes: list[ConversionNode] = []
    for child in parent.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                nodes.append(ConversionNode(
                    node_type="paragraph",
                    rich_text=[_plain_rt(str(child))],
                ))
        elif isinstance(child, Tag):
            parsed = _parse_tag(child)
            if parsed is not None:
                nodes.extend(parsed if isinstance(parsed, list) else [parsed])
    return nodes


def _parse_tag(tag: Tag) -> ConversionNode | list[ConversionNode] | None:
    name = tag.name

    # --- 見出し ---
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        rt = _parse_rich_text(tag)
        if level <= 3:
            return ConversionNode(node_type=f"heading_{level}", rich_text=rt)
        # H4〜H6 → 太字 paragraph（Notion に H4〜H6 なし）
        for r in rt:
            r.setdefault("annotations", {})["bold"] = True
        return ConversionNode(node_type="paragraph", rich_text=rt)

    # --- 段落 ---
    if name == "p":
        rt = _parse_rich_text(tag)
        if not rt:
            return None
        return ConversionNode(node_type="paragraph", rich_text=rt)

    # --- 引用 ---
    if name == "blockquote":
        rt = _parse_rich_text(tag)
        return ConversionNode(node_type="quote", rich_text=rt)

    # --- 水平線 ---
    if name == "hr":
        return ConversionNode(node_type="divider")

    # --- 箇条書き ---
    if name == "ul":
        return _parse_list(tag, "bulleted_list_item")

    # --- 番号付きリスト ---
    if name == "ol":
        return _parse_list(tag, "numbered_list_item")

    # --- タスクリスト ---
    if name == "ac:task-list":
        return _parse_task_list(tag)

    # --- テーブル ---
    if name == "table":
        return _parse_table(tag)

    # --- レイアウト（カラム） ---
    if name == "ac:layout":
        return _parse_layout(tag)

    # --- マクロ ---
    if name == "ac:structured-macro":
        return _parse_macro(tag)

    # --- 画像 ---
    if name == "ac:image":
        return _parse_image(tag)

    # --- リンク ---
    if name == "ac:link":
        return None  # リンクはインライン要素として rich_text 内で処理

    # --- その他のブロックレベル要素は子を再帰処理 ---
    if name in ("div", "section", "article", "ac:layout-section", "ac:layout-cell"):
        return _parse_children(tag)

    return None


# ──────────────────────────────────────────────
# リスト
# ──────────────────────────────────────────────

def _parse_list(tag: Tag, list_type: str) -> list[ConversionNode]:
    nodes = []
    for li in tag.find_all("li", recursive=False):
        rt = _parse_rich_text(li)
        # ネストされたリストを子ノードとして処理
        children = []
        for sub in li.find_all(["ul", "ol"], recursive=False):
            sub_type = "bulleted_list_item" if sub.name == "ul" else "numbered_list_item"
            children.extend(_parse_list(sub, sub_type))
        nodes.append(ConversionNode(
            node_type=list_type,
            rich_text=rt,
            children=children,
        ))
    return nodes


def _parse_task_list(tag: Tag) -> list[ConversionNode]:
    nodes = []
    for task in tag.find_all("ac:task", recursive=False):
        status_tag = task.find("ac:task-status")
        checked = status_tag and status_tag.get_text(strip=True) == "complete"
        body_tag = task.find("ac:task-body")
        rt = _parse_rich_text(body_tag) if body_tag else []
        nodes.append(ConversionNode(
            node_type="to_do",
            rich_text=rt,
            attrs={"checked": checked},
        ))
    return nodes


# ──────────────────────────────────────────────
# テーブル
# ──────────────────────────────────────────────

def _parse_table(tag: Tag) -> ConversionNode:
    rows_tags = tag.find_all("tr")
    rows: list[ConversionNode] = []
    has_row_header = False

    for i, tr in enumerate(rows_tags):
        cells = tr.find_all(["td", "th"])
        if any(c.name == "th" for c in cells):
            has_row_header = True
        cell_nodes = [
            ConversionNode(node_type="table_cell", rich_text=_parse_rich_text(c))
            for c in cells
        ]
        rows.append(ConversionNode(node_type="table_row", children=cell_nodes))

    table_width = max((len(r.children) for r in rows), default=0)
    return ConversionNode(
        node_type="table",
        children=rows,
        attrs={"table_width": table_width, "has_row_header": has_row_header},
    )


# ──────────────────────────────────────────────
# レイアウト（2カラム・3カラム等）
# ──────────────────────────────────────────────

def _parse_layout(tag: Tag) -> list[ConversionNode]:
    sections = tag.find_all("ac:layout-section", recursive=False)
    if not sections:
        return _parse_children(tag)

    all_nodes = []
    for section in sections:
        cells = section.find_all("ac:layout-cell", recursive=False)
        if len(cells) <= 1:
            # 1カラム: 通常のブロックとして展開
            all_nodes.extend(_parse_children(section))
        else:
            # 複数カラム: column_list に変換
            column_children = [
                ConversionNode(node_type="column", children=_parse_children(cell))
                for cell in cells
            ]
            all_nodes.append(ConversionNode(node_type="column_list", children=column_children))
    return all_nodes


# ──────────────────────────────────────────────
# マクロ
# ──────────────────────────────────────────────

def _parse_macro(tag: Tag) -> ConversionNode | list[ConversionNode] | None:
    macro_name = tag.get("ac:name", "")

    # 未対応マクロ → 警告 callout
    if macro_name in UNSUPPORTED_MACROS:
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt(f"[移行不可] {macro_name} マクロは Notion 非対応です。手動での対応が必要です。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # 情報パネル系 (info / tip / note / warning / panel)
    if macro_name in COLOR_MAP:
        body_tag = tag.find("ac:rich-text-body")
        children = _parse_children(body_tag) if body_tag else []
        # パネル本文の最初の paragraph を rich_text として使い、残りを子に
        rt: list[dict] = []
        remaining: list[ConversionNode] = []
        if children and children[0].node_type == "paragraph":
            rt = children[0].rich_text
            remaining = children[1:]
        else:
            remaining = children
        return ConversionNode(
            node_type="callout",
            rich_text=rt,
            children=remaining,
            attrs={
                "color": COLOR_MAP[macro_name],
                "emoji": EMOJI_MAP.get(macro_name, "📋"),
            },
        )

    # expand → toggle
    if macro_name == "expand":
        title_tag = tag.find("ac:parameter", {"ac:name": "title"})
        title_text = title_tag.get_text(strip=True) if title_tag else "詳細を表示"
        body_tag = tag.find("ac:rich-text-body")
        children = _parse_children(body_tag) if body_tag else []
        return ConversionNode(
            node_type="toggle",
            rich_text=[_plain_rt(title_text)],
            children=children,
        )

    # code → コードブロック
    if macro_name == "code":
        lang_tag = tag.find("ac:parameter", {"ac:name": "language"})
        title_tag = tag.find("ac:parameter", {"ac:name": "title"})
        body_tag = tag.find("ac:plain-text-body")
        lang = normalize_language(lang_tag.get_text(strip=True) if lang_tag else None)
        code_text = body_tag.get_text() if body_tag else ""
        caption = []
        if title_tag:
            caption = [_plain_rt(title_tag.get_text(strip=True))]
        return ConversionNode(
            node_type="code",
            rich_text=[_plain_rt(code_text)],
            attrs={"language": lang, "caption": caption},
        )

    # children（子ページ一覧） → child_page_list（builder 側で subpages ブロックに変換）
    if macro_name == "children":
        return ConversionNode(node_type="child_page_list")

    # widget → embed
    if macro_name == "widget":
        url_tag = tag.find("ac:parameter", {"ac:name": "url"})
        url = url_tag.get_text(strip=True) if url_tag else ""
        return ConversionNode(node_type="embed", attrs={"url": url})

    # include ページ → 警告 callout（synced block は API 経由での作成が困難）
    if macro_name == "include":
        page_tag = tag.find("ri:page")
        title = page_tag.get("ri:content-title", "不明なページ") if page_tag else "不明なページ"
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt(f"[移行要確認] Include マクロ: 元ページ「{title}」の内容を手動で埋め込んでください。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # roadmap → 警告 callout
    if macro_name == "roadmap":
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt("[移行不可] roadmap マクロは Notion 非対応です。Notion の timeline ビューで代替してください。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # details（Page Properties） → 警告 callout
    if macro_name in ("details", "detailssummary"):
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt(f"[移行要確認] {macro_name} マクロ: Notion DB のプロパティへの移行が必要です。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # contentbylabel → 警告 callout
    if macro_name == "contentbylabel":
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt("[移行不可] contentbylabel マクロは Notion 非対応です。Notion DB のフィルタビューで代替してください。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # livesearch → 警告 callout
    if macro_name == "livesearch":
        return ConversionNode(
            node_type="callout",
            rich_text=[_plain_rt("[移行不可] livesearch マクロは Notion 非対応です。")],
            attrs={"color": "orange_background", "emoji": "⚠️"},
        )

    # 未知のマクロ → rich-text-body があれば展開、なければ警告
    body_tag = tag.find("ac:rich-text-body")
    if body_tag:
        return _parse_children(body_tag)

    return ConversionNode(
        node_type="callout",
        rich_text=[_plain_rt(f"[移行要確認] {macro_name} マクロ: 手動での確認が必要です。")],
        attrs={"color": "orange_background", "emoji": "⚠️"},
    )


# ──────────────────────────────────────────────
# 画像
# ──────────────────────────────────────────────

def _parse_image(tag: Tag) -> ConversionNode | None:
    attachment = tag.find("ri:attachment")
    url_tag = tag.find("ri:url")
    caption_tag = tag.find("ac:caption")
    caption = _parse_rich_text(caption_tag) if caption_tag else []

    if url_tag:
        url = url_tag.get("ri:value", "")
        return ConversionNode(
            node_type="image",
            attrs={"type": "external", "url": url, "caption": caption},
        )
    if attachment:
        filename = attachment.get("ri:filename", "")
        return ConversionNode(
            node_type="image",
            attrs={"type": "attachment", "filename": filename, "caption": caption},
        )
    return None


# ──────────────────────────────────────────────
# rich_text の構築
# ──────────────────────────────────────────────

_DEFAULT_ANNOTATIONS = {
    "bold": False,
    "italic": False,
    "strikethrough": False,
    "underline": False,
    "code": False,
    "color": "default",
}


def _plain_rt(text: str) -> dict:
    return {
        "type": "text",
        "text": {"content": text, "link": None},
        "annotations": dict(_DEFAULT_ANNOTATIONS),
        "plain_text": text,
    }


def _parse_rich_text(tag: Tag | None) -> list[dict]:
    if tag is None:
        return []
    results: list[dict] = []
    _collect_rich_text(tag, dict(_DEFAULT_ANNOTATIONS), None, results)
    return results


def _collect_rich_text(
    node: Tag | NavigableString,
    annotations: dict,
    link_url: str | None,
    out: list[dict],
) -> None:
    if isinstance(node, NavigableString):
        text = str(node)
        if text:
            out.append({
                "type": "text",
                "text": {"content": text, "link": {"url": link_url} if link_url else None},
                "annotations": dict(annotations),
                "plain_text": text,
            })
        return

    tag_name = node.name
    new_annotations = dict(annotations)
    new_link = link_url

    if tag_name in ("strong", "b"):
        new_annotations["bold"] = True
    elif tag_name in ("em", "i"):
        new_annotations["italic"] = True
    elif tag_name == "s":
        new_annotations["strikethrough"] = True
    elif tag_name == "u":
        # Notion は下線非対応 → アノテーションは変更せずプレーンテキストとして扱う
        pass
    elif tag_name == "code":
        new_annotations["code"] = True
    elif tag_name == "sup":
        # 上付き文字: Notion に専用アノテーションなし。テキストそのままで表現
        pass
    elif tag_name == "sub":
        # 下付き文字: 同上
        pass
    elif tag_name == "span":
        # テキストカラーは無視（Notion は限定カラーのみ）
        pass
    elif tag_name == "a":
        new_link = node.get("href")
    elif tag_name in ("ac:link",):
        # 内部リンク（ページリンク）→ テキストのみ抽出
        page_tag = node.find("ri:page")
        link_text = page_tag.get("ri:content-title", "") if page_tag else ""
        if link_text:
            out.append({
                "type": "text",
                "text": {"content": link_text, "link": None},
                "annotations": dict(annotations),
                "plain_text": link_text,
            })
        return
    elif tag_name in ("br",):
        out.append({
            "type": "text",
            "text": {"content": "\n", "link": None},
            "annotations": dict(annotations),
            "plain_text": "\n",
        })
        return
    elif tag_name in ("ac:structured-macro",):
        # インラインマクロ（anchor 等）はテキストとして無視
        return
    elif tag_name in ("p", "div", "li", "td", "th", "ac:task-body"):
        # ブロック要素がインラインコンテキストにある場合は子を再帰処理
        pass
    elif tag_name in ("ri:user",):
        user_name = node.get("ri:username", node.get("ri:userkey", ""))
        if user_name:
            out.append({
                "type": "mention",
                "mention": {"type": "user", "user": {"id": user_name}},
                "annotations": dict(annotations),
                "plain_text": f"@{user_name}",
            })
        return

    for child in node.children:
        _collect_rich_text(child, new_annotations, new_link, out)
