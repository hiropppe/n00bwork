"""E2Eテスト: テーブルの移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "基本テーブル",
    "xml": """
    <table>
      <tbody>
        <tr><td>A1</td><td>A2</td></tr>
        <tr><td>B1</td><td>B2</td></tr>
      </tbody>
    </table>
    """,
}], indirect=True)
def test_basic_table_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "table"
    assert blocks[0]["table"]["table_width"] == 2
    rows = notion_client.get_blocks(blocks[0]["id"])
    assert len(rows) == 2
    assert rows[0]["type"] == "table_row"
    assert rows[0]["table_row"]["cells"][0][0]["plain_text"] == "A1"
    assert rows[0]["table_row"]["cells"][1][0]["plain_text"] == "A2"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "ヘッダー行あきテーブル",
    "xml": """
    <table>
      <tbody>
        <tr><th>名前</th><th>値</th></tr>
        <tr><td>foo</td><td>bar</td></tr>
      </tbody>
    </table>
    """,
}], indirect=True)
def test_table_with_header_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "table"
    assert blocks[0]["table"]["has_column_header"] is True
    assert blocks[0]["table"]["table_width"] == 2
