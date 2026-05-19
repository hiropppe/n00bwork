"""E2Eテスト: リストの移行検証"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "箇条書きリスト",
    "xml": "<ul><li>項目A</li><li>項目B</li></ul>",
}], indirect=True)
def test_bulleted_list_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "bulleted_list_item"
    assert blocks[0]["bulleted_list_item"]["rich_text"][0]["plain_text"] == "項目A"
    assert blocks[1]["type"] == "bulleted_list_item"
    assert blocks[1]["bulleted_list_item"]["rich_text"][0]["plain_text"] == "項目B"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "番号付きリスト",
    "xml": "<ol><li>手順1</li><li>手順2</li></ol>",
}], indirect=True)
def test_numbered_list_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "numbered_list_item"
    assert blocks[0]["numbered_list_item"]["rich_text"][0]["plain_text"] == "手順1"
    assert blocks[1]["type"] == "numbered_list_item"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "ネストリスト",
    "xml": "<ul><li>親項目<ul><li>子項目</li></ul></li></ul>",
}], indirect=True)
def test_nested_list_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert blocks[0]["type"] == "bulleted_list_item"
    assert blocks[0]["has_children"] is True
    children = notion_client.get_blocks(blocks[0]["id"])
    assert children[0]["type"] == "bulleted_list_item"
    assert children[0]["bulleted_list_item"]["rich_text"][0]["plain_text"] == "子項目"


@pytest.mark.parametrize("migrated_notion_page", [{
    "title": "タスクリスト",
    "xml": """
    <ac:task-list>
      <ac:task>
        <ac:task-id>1</ac:task-id>
        <ac:task-status>incomplete</ac:task-status>
        <ac:task-body>未完了タスク</ac:task-body>
      </ac:task>
      <ac:task>
        <ac:task-id>2</ac:task-id>
        <ac:task-status>complete</ac:task-status>
        <ac:task-body>完了タスク</ac:task-body>
      </ac:task>
    </ac:task-list>
    """,
}], indirect=True)
def test_task_list_e2e(migrated_notion_page, notion_client):
    blocks = notion_client.get_blocks(migrated_notion_page)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "to_do"
    assert blocks[0]["to_do"]["checked"] is False
    assert blocks[0]["to_do"]["rich_text"][0]["plain_text"] == "未完了タスク"
    assert blocks[1]["type"] == "to_do"
    assert blocks[1]["to_do"]["checked"] is True
    assert blocks[1]["to_do"]["rich_text"][0]["plain_text"] == "完了タスク"
