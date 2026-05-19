"""E2Eテスト: マクロの移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "tipマクロ",
    "xml": """
    <ac:structured-macro ac:name="tip">
      <ac:rich-text-body><p>ヒントメッセージ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_tip_macro_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["color"] == "green_background"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "noteマクロ",
    "xml": """
    <ac:structured-macro ac:name="note">
      <ac:rich-text-body><p>注意メッセージ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_note_macro_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["color"] == "yellow_background"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "warningマクロ",
    "xml": """
    <ac:structured-macro ac:name="warning">
      <ac:rich-text-body><p>警告メッセージ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_warning_macro_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["color"] == "red_background"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "panelマクロ",
    "xml": """
    <ac:structured-macro ac:name="panel">
      <ac:rich-text-body><p>パネルコンテンツ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_panel_macro_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["color"] == "gray_background"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "expandマクロ",
    "xml": """
    <ac:structured-macro ac:name="expand">
      <ac:parameter ac:name="title">クリックして展開</ac:parameter>
      <ac:rich-text-body><p>折りたたまれたコンテンツ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_expand_macro_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "toggle"
    rt = blocks[0]["toggle"]["rich_text"]
    assert any("クリックして展開" in r["plain_text"] for r in rt)
