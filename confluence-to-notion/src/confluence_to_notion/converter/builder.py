"""ConversionNode（中間表現）→ Notion Block API JSON"""

from __future__ import annotations
from .parser import ConversionNode

# Notion API の blocks.children.append が一度に受け付ける最大ブロック数
_NOTION_MAX_CHILDREN = 100


def build_notion_blocks(nodes: list[ConversionNode]) -> list[dict]:
    """ConversionNode リストを Notion Block JSON リストに変換する"""
    return [b for node in nodes for b in _build_block(node)]


def _build_block(node: ConversionNode) -> list[dict]:
    t = node.node_type

    if t == "paragraph":
        return [_paragraph(node.rich_text)]

    if t in ("heading_1", "heading_2", "heading_3"):
        level = int(t[-1])
        return [{
            "object": "block",
            "type": t,
            t: {"rich_text": node.rich_text, "color": "default"},
        }]

    if t == "quote":
        return [{"object": "block", "type": "quote", "quote": {"rich_text": node.rich_text}}]

    if t == "divider":
        return [{"object": "block", "type": "divider", "divider": {}}]

    if t == "code":
        return [{
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": node.rich_text,
                "language": node.attrs.get("language", "plain text"),
                "caption": node.attrs.get("caption", []),
            },
        }]

    if t == "bulleted_list_item":
        block = {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": node.rich_text},
        }
        if node.children:
            block["bulleted_list_item"]["children"] = build_notion_blocks(node.children)
        return [block]

    if t == "numbered_list_item":
        block = {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": node.rich_text},
        }
        if node.children:
            block["numbered_list_item"]["children"] = build_notion_blocks(node.children)
        return [block]

    if t == "to_do":
        return [{
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": node.rich_text,
                "checked": node.attrs.get("checked", False),
            },
        }]

    if t == "callout":
        block = {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": node.rich_text,
                "icon": {"type": "emoji", "emoji": node.attrs.get("emoji", "📋")},
                "color": node.attrs.get("color", "gray_background"),
            },
        }
        if node.children:
            block["callout"]["children"] = build_notion_blocks(node.children)
        return [block]

    if t == "toggle":
        block = {
            "object": "block",
            "type": "toggle",
            "toggle": {"rich_text": node.rich_text},
        }
        if node.children:
            block["toggle"]["children"] = build_notion_blocks(node.children)
        return [block]

    if t == "table":
        rows = build_notion_blocks(node.children)
        return [{
            "object": "block",
            "type": "table",
            "table": {
                "table_width": node.attrs.get("table_width", 1),
                "has_column_header": False,
                "has_row_header": node.attrs.get("has_row_header", False),
                "children": rows,
            },
        }]

    if t == "table_row":
        cells = [
            {"type": "table_cell", "table_cell": {"rich_text": cell.rich_text}}
            for cell in node.children
        ]
        return [{"object": "block", "type": "table_row", "table_row": {"cells": [
            cell["table_cell"]["rich_text"] for cell in cells
        ]}}]

    if t == "column_list":
        columns = []
        for col_node in node.children:
            col_content = build_notion_blocks(col_node.children)
            columns.append({
                "object": "block",
                "type": "column",
                "column": {"children": col_content},
            })
        return [{
            "object": "block",
            "type": "column_list",
            "column_list": {"children": columns},
        }]

    if t == "column":
        return build_notion_blocks(node.children)

    if t == "embed":
        url = node.attrs.get("url", "")
        if not url:
            return []
        return [{"object": "block", "type": "embed", "embed": {"url": url}}]

    if t == "image":
        image_type = node.attrs.get("type", "external")
        caption = node.attrs.get("caption", [])
        if image_type == "external":
            return [{
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": node.attrs.get("url", "")},
                    "caption": caption,
                },
            }]
        # 添付ファイルは後で URL 解決が必要。ここでは空リストを返す
        return []

    if t == "child_page_list":
        # Notion には "sub_pages" ブロックが存在しない。
        # children マクロは移行後のページツリーで自然に表現される。
        # ここでは注記 callout を挿入する。
        return [{
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": "[children マクロ] 子ページの一覧はサイドバーのページツリーで確認できます。"}, "annotations": _default_annotations(), "plain_text": ""}],
                "icon": {"type": "emoji", "emoji": "📑"},
                "color": "blue_background",
            },
        }]

    return []


def _paragraph(rich_text: list[dict]) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text},
    }


def _default_annotations() -> dict:
    return {
        "bold": False, "italic": False, "strikethrough": False,
        "underline": False, "code": False, "color": "default",
    }
