"""E2Eテスト: 基本テキスト書式の移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "太字テキスト",
    "xml": "<p><strong>太字テキスト</strong></p>",
}], indirect=True)
def test_bold_text_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "paragraph"
    rt = blocks[0]["paragraph"]["rich_text"][0]
    assert rt["plain_text"] == "太字テキスト"
    assert rt["annotations"]["bold"] is True


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "コードブロック",
    "xml": """
    <ac:structured-macro ac:name="code">
      <ac:parameter ac:name="language">python</ac:parameter>
      <ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_code_block_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "python"
    assert 'print("hello")' in blocks[0]["code"]["rich_text"][0]["plain_text"]


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "infoパネル",
    "xml": """
    <ac:structured-macro ac:name="info">
      <ac:rich-text-body><p>情報メッセージ</p></ac:rich-text-body>
    </ac:structured-macro>
    """,
}], indirect=True)
def test_info_macro_to_callout_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "callout"
    assert blocks[0]["callout"]["color"] == "blue_background"
