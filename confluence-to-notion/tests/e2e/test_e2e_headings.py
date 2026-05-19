"""E2Eテスト: 見出しの移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "H1見出し",
    "xml": "<h1>見出し1</h1>",
}], indirect=True)
def test_h1_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "heading_1"
    assert blocks[0]["heading_1"]["rich_text"][0]["plain_text"] == "見出し1"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "H2見出し",
    "xml": "<h2>見出し2</h2>",
}], indirect=True)
def test_h2_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "heading_2"
    assert blocks[0]["heading_2"]["rich_text"][0]["plain_text"] == "見出し2"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "H3見出し",
    "xml": "<h3>見出し3</h3>",
}], indirect=True)
def test_h3_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "heading_3"
    assert blocks[0]["heading_3"]["rich_text"][0]["plain_text"] == "見出し3"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "H4見出し（paragraphフォールバック）",
    "xml": "<h4>見出し4</h4>",
}], indirect=True)
def test_h4_fallback_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "paragraph"
    rt = blocks[0]["paragraph"]["rich_text"][0]
    assert rt["plain_text"] == "見出し4"
    assert rt["annotations"]["bold"] is True
