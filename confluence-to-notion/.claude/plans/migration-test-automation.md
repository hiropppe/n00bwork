# 移行テスト自動化アーキテクチャの構築

## Context

Confluence DC → Notion 移行における「ページの見た目と機能を Notion に再現できるか」を体系的・自動的に検証するためのテスト基盤を構築する。
テストリスト（docs/migration-test-list.md、全110項目）の各項目を、変換ロジックのユニットテストと実APIを使ったE2Eテストの2層で自動検証できるようにする。

---

## テスト構造の全体像

```
Layer 1: ユニットテスト（API不要・高速）
  XML スニペット → parser.py → 中間表現 → builder.py → Notion Block JSON
                                                          ↑
                                                  pytest でアサート

Layer 2: E2Eテスト（実API使用・pytest -m e2e で分離）
  fixture: Confluence でテストページ作成（Storage Format XML を直接送信）
    → migration.py の migrate_page() を呼び出し
    → Notion API でブロック構造を取得・アサート
    → fixture teardown: Confluence・Notion 両方のテストページを削除
```

**Playwright は不要** — `atlassian-python-api` の `create_page()` で任意の Storage Format XML を直接送れるため、UIを介した操作は不要。

**✕困難項目の方針** — 変換不可なマクロ（TOC・anchor等）は削除せず、橙色の警告 callout ブロックに変換して移行後に気づけるようにする。

---

## ディレクトリ構成

```
src/
  confluence_to_notion/
    converter/
      parser.py      # Storage Format XML → ConversionNode（中間表現）
      builder.py     # ConversionNode → Notion Block API JSON
      mappings.py    # 定数マップ（言語名・カラー・マクロ種別等）
    client/
      confluence.py  # ConfluenceClient（create/get/delete ラッパー）
      notion.py      # NotionClient（get_blocks・assert・delete ラッパー）
    migration.py     # migrate_page(confluence_id, notion_parent_id) → notion_id

tests/
  conftest.py                   # .env 読み込み・e2e マーカー定義
  unit/
    conftest.py                 # convert(xml) ショートカット
    fixtures/                   # .xml スニペット（テストデータ）
    test_text.py                # 3-1〜3-10: 見出し・インラインアノテーション
    test_code.py                # 3-11〜3-14: コードブロック
    test_lists.py               # 3-15〜3-18: リスト・タスクリスト
    test_tables.py              # 3-19〜3-25: テーブル
    test_misc_format.py         # 3-26〜3-28: 引用・水平線・絵文字
    test_links.py               # カテゴリ4: リンク
    test_macros.py              # カテゴリ6: マクロ
    test_layout.py              # カテゴリ2: レイアウト（カラム）
  e2e/
    conftest.py                 # migrated_notion_page fixture（作成→移行→teardown）
    test_e2e_text.py
    test_e2e_macros.py
    test_e2e_tables.py
```

---

## pyproject.toml への変更

```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-dotenv>=0.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["e2e: end-to-end tests requiring live Confluence and Notion APIs"]
env_files = [".env"]
```

---

## 各ファイルの実装内容

### `src/confluence_to_notion/converter/mappings.py`

```python
LANGUAGE_MAP = {"java": "java", "none": "plain text", "cobol": "plain text", ...}
COLOR_MAP = {
    "info": "blue_background", "tip": "green_background",
    "note": "yellow_background", "warning": "red_background",
    "panel": "gray_background",
}
PANEL_EMOJI_MAP = {"info": "ℹ️", "tip": "💡", "note": "⚠️", "warning": "🚨"}
UNSUPPORTED_MACRO_NAMES = {"toc", "pagetree", "livesearch", "taskreport", ...}
```

### `src/confluence_to_notion/converter/parser.py`

BeautifulSoup（lxml バックエンド）で Storage Format XML を解析し `list[ConversionNode]` を返す。

**重要**: `lxml-xml` パーサーは `ac:` プレフィックスを除去してしまうため、`lxml`（HTMLパーサー）を使用する。
また、`lxml` HTML パーサーは CDATA をサポートしないため、`_preprocess_cdata()` で前処理が必要。

```python
@dataclass
class ConversionNode:
    node_type: str          # "paragraph", "heading_1", "code_block", "callout", ...
    rich_text: list[dict]   # Notion rich_text 構造
    children: list["ConversionNode"]
    attrs: dict             # 言語・レベル・カラー等のメタ情報
```

### `src/confluence_to_notion/converter/builder.py`

`ConversionNode` リスト → Notion Block API JSON リスト。ユニットテストはこの出力を直接比較する。

### `src/confluence_to_notion/client/confluence.py`

```python
class ConfluenceClient:
    def create_test_page(self, space, title, storage_xml) -> str: ...
    def delete_page(self, page_id) -> None: ...
    def get_page_storage_xml(self, page_id) -> str: ...
```

### `src/confluence_to_notion/client/notion.py`

```python
class NotionClient:
    def get_blocks(self, page_id) -> list[dict]: ...  # has_more 対応
    def delete_page(self, page_id) -> None: ...       # アーカイブ
```

---

## ユニットテストの実装例

### `tests/unit/conftest.py`

```python
def convert(xml_snippet: str) -> list[dict]:
    full_xml = f'<root xmlns:ac="..." xmlns:ri="...">{xml_snippet}</root>'
    return build_notion_blocks(parse_storage_xml(full_xml))
```

### テストケース例（`test_text.py`）

```python
def test_bold():
    result = convert('<p><strong>太字</strong></p>')
    assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True

def test_h4_falls_back_to_bold_paragraph():
    result = convert('<h4>見出し4</h4>')
    assert result[0]["type"] == "paragraph"
    assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True

def test_underline_becomes_plain_text():
    result = convert('<p><u>下線</u></p>')
    rt = result[0]["paragraph"]["rich_text"][0]
    assert rt["text"]["content"] == "下線"
    assert rt["annotations"]["bold"] is False
```

### テストケース例（`test_macros.py`）

```python
@pytest.mark.parametrize("macro_name,color,emoji", [
    ("info",    "blue_background",   "ℹ️"),
    ("tip",     "green_background",  "💡"),
    ("warning", "red_background",    "🚨"),
])
def test_panel_to_callout(macro_name, color, emoji):
    xml = f'<ac:structured-macro ac:name="{macro_name}"><ac:rich-text-body><p>本文</p></ac:rich-text-body></ac:structured-macro>'
    result = convert(xml)
    assert result[0]["type"] == "callout"
    assert result[0]["callout"]["color"] == color

def test_toc_becomes_unsupported_callout():
    result = convert('<ac:structured-macro ac:name="toc"/>')
    assert result[0]["type"] == "callout"
    assert result[0]["callout"]["color"] == "orange_background"
    assert "移行不可" in result[0]["callout"]["rich_text"][0]["text"]["content"]

def test_expand_to_toggle():
    xml = '''<ac:structured-macro ac:name="expand">
      <ac:parameter ac:name="title">展開タイトル</ac:parameter>
      <ac:rich-text-body><p>本文</p></ac:rich-text-body>
    </ac:structured-macro>'''
    result = convert(xml)
    assert result[0]["type"] == "toggle"
    assert result[0]["toggle"]["children"][0]["type"] == "paragraph"
```

---

## E2Eテストの実装例

### `tests/e2e/conftest.py` — `migrated_notion_page` fixture

```python
@pytest.fixture()
def migrated_notion_page(request, confluence_client, notion_client, migration_runner):
    xml_body = request.param["xml"]
    title = f"[E2E] {request.param['title']} {int(time.time())}"

    confluence_page_id = confluence_client.create_test_page("SPC", title, xml_body)
    notion_page_id = migration_runner.migrate_page(
        confluence_page_id, os.environ["NOTION_TEST_PAGE_ID"]
    )
    yield notion_page_id

    confluence_client.delete_page(confluence_page_id)
    notion_client.delete_page(notion_page_id)
```

### `tests/e2e/test_e2e_text.py`

```python
pytestmark = pytest.mark.e2e

@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "コードブロック",
    "xml": '<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[print("hi")]]></ac:plain-text-body></ac:structured-macro>'
}], indirect=True)
def test_code_block_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
```

---

## ✕困難項目の変換方針

変換不可なマクロ・要素は削除せず、橙色の警告 callout に変換することで移行後に確認できるようにする。

```python
# TOC、アンカー、pagetree 等
{
    "type": "callout",
    "callout": {
        "icon": {"emoji": "⚠️"},
        "color": "orange_background",
        "rich_text": [{"text": {"content": "[移行不可] TOC マクロは Notion 非対応です。手動で目次を作成してください。"}}]
    }
}
```

| 項目 | 変換方針 |
|------|---------|
| 3-4 下線 | プレーンテキストに（アノテーション落とし） |
| 3-12 コードタイトル | `caption` フィールドに移動 |
| 3-20/3-21 セル結合 | 結合を無視してフラットなテーブルに変換 |
| 4-2/4-3 アンカーリンク | テキストとして保持（href を除去） |
| 6-7 TOC 等 | 警告 callout に変換 |

---

## 実装フェーズ

### フェーズ1: 基盤構築 + 基本書式（○/L）— 完了 ✅

対象テストリスト項目: 3-1〜3-3, 3-5, 3-8, 3-9, 3-11, 3-15〜3-17, 3-19, 3-22, 3-26, 4-4

1. `pyproject.toml` に `pytest` 追加 → コンテナ再ビルド ✅
2. `src/` + `tests/` ディレクトリ骨格を作成 ✅
3. `mappings.py` → `parser.py` → `builder.py` の順で実装（TDD）✅
4. ユニットテスト 61/61 PASS ✅
5. E2E fixture を実装（tests/e2e/conftest.py）✅

**解決した技術的課題:**
- `lxml-xml` パーサーは `ac:` プレフィックスを除去 → `lxml` に変更
- `lxml` HTML パーサーは `<html><body>` でラップ → `soup.find("root")` で明示的に探索
- `lxml` HTML パーサーは CDATA 非対応 → `_preprocess_cdata()` で前処理

### フェーズ2: 頻出マクロ変換（△/M）

対象: 6-1〜6-6（info/tip/note/warning/panel/expand）、3-2（H4-H6）、3-27（水平線）、2-2（2カラム）、実環境で確認されたマクロ（widget, roadmap, children, anchor等）

### フェーズ3: 困難項目の方針実装（✕/H）

対象: 警告 callout 変換、セル結合のフラット化、下線の除去等

---

## 実行コマンド

```bash
# ユニットテストのみ（高速・API不要）
uv run pytest tests/unit/ -v

# E2Eテスト（実API・ローカルのみ）
uv run pytest tests/e2e/ -v -m e2e

# 全テスト
uv run pytest -v
```

---

## 変更対象ファイル

| ファイル | 変更種別 | 状態 |
|---------|---------|------|
| `pyproject.toml` | pytest 追加 | ✅ |
| `src/confluence_to_notion/converter/mappings.py` | 新規 | ✅ |
| `src/confluence_to_notion/converter/parser.py` | 新規 | ✅ |
| `src/confluence_to_notion/converter/builder.py` | 新規 | ✅ |
| `src/confluence_to_notion/client/confluence.py` | 新規 | ✅ |
| `src/confluence_to_notion/client/notion.py` | 新規 | ✅ |
| `src/confluence_to_notion/migration.py` | 新規 | ✅ |
| `tests/conftest.py` | 新規 | ✅ |
| `tests/unit/conftest.py` | 新規 | ✅ |
| `tests/unit/test_text.py` 他 | 新規 | ✅ |
| `tests/e2e/conftest.py` | 新規 | ✅ |
| `tests/e2e/test_e2e_text.py` 他 | 新規 | ✅ |
