"""E2Eテスト: レイアウト（カラム）の移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize(
    "migrated_notion_page",
    [
        {
            "title": "2カラムレイアウト",
            "xml": """
    <ac:layout>
      <ac:layout-section ac:type="two_equal">
        <ac:layout-cell><p>左カラム</p></ac:layout-cell>
        <ac:layout-cell><p>右カラム</p></ac:layout-cell>
      </ac:layout-section>
    </ac:layout>
    """,
        }
    ],
    indirect=True,
)
def test_two_column_layout_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "column_list"
    assert blocks[0]["has_children"] is True

    columns = notion_client.get_blocks(blocks[0]["id"])
    assert len(columns) == 2
    assert all(c["type"] == "column" for c in columns)

    left = notion_client.get_blocks(columns[0]["id"])
    assert left[0]["type"] == "paragraph"
    assert left[0]["paragraph"]["rich_text"][0]["plain_text"] == "左カラム"

    right = notion_client.get_blocks(columns[1]["id"])
    assert right[0]["type"] == "paragraph"
    assert right[0]["paragraph"]["rich_text"][0]["plain_text"] == "右カラム"


@pytest.mark.parametrize(
    "migrated_notion_page",
    [
        {
            "title": "1カラムレイアウト",
            "xml": """
    <ac:layout>
      <ac:layout-section ac:type="single">
        <ac:layout-cell><p>全幅テキスト</p></ac:layout-cell>
      </ac:layout-section>
    </ac:layout>
    """,
        }
    ],
    indirect=True,
)
def test_single_column_layout_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["paragraph"]["rich_text"][0]["plain_text"] == "全幅テキスト"


@pytest.mark.parametrize(
    "migrated_notion_page",
    [
        {
            "title": "1カラム+2カラム混在レイアウト",
            "xml": """
    <ac:layout>
      <ac:layout-section ac:type="single">
        <ac:layout-cell><p>全幅テキスト</p></ac:layout-cell>
      </ac:layout-section>
      <ac:layout-section ac:type="two_equal">
        <ac:layout-cell><p>左</p></ac:layout-cell>
        <ac:layout-cell><p>右</p></ac:layout-cell>
      </ac:layout-section>
    </ac:layout>
    """,
        }
    ],
    indirect=True,
)
def test_mixed_sections_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "paragraph"
    assert blocks[1]["type"] == "column_list"
    columns = notion_client.get_blocks(blocks[1]["id"])
    assert len(columns) == 2
