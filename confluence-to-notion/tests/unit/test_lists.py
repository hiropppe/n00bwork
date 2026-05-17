"""テストリスト 3-15〜3-18: リスト・タスクリストの変換テスト"""

import pytest
from tests.unit.conftest import convert


class TestBulletedList:
    """3-15: 箇条書き（ネスト対応）"""

    def test_simple_bulleted_list(self):
        result = convert("<ul><li>項目A</li><li>項目B</li></ul>")
        assert result[0]["type"] == "bulleted_list_item"
        assert result[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "項目A"
        assert result[1]["type"] == "bulleted_list_item"
        assert result[1]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "項目B"

    def test_nested_bulleted_list(self):
        xml = """
        <ul>
          <li>親項目
            <ul>
              <li>子項目1</li>
              <li>子項目2</li>
            </ul>
          </li>
        </ul>
        """
        result = convert(xml)
        assert result[0]["type"] == "bulleted_list_item"
        children = result[0]["bulleted_list_item"]["children"]
        assert len(children) == 2
        assert children[0]["type"] == "bulleted_list_item"
        assert children[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "子項目1"


class TestNumberedList:
    """3-16: 番号付きリスト（ネスト対応）"""

    def test_simple_numbered_list(self):
        result = convert("<ol><li>手順1</li><li>手順2</li></ol>")
        assert result[0]["type"] == "numbered_list_item"
        assert result[0]["numbered_list_item"]["rich_text"][0]["text"]["content"] == "手順1"
        assert result[1]["type"] == "numbered_list_item"

    def test_nested_numbered_list(self):
        xml = """
        <ol>
          <li>Step 1
            <ol>
              <li>Step 1-1</li>
            </ol>
          </li>
        </ol>
        """
        result = convert(xml)
        children = result[0]["numbered_list_item"]["children"]
        assert children[0]["type"] == "numbered_list_item"


class TestTaskList:
    """3-17: タスクリスト（チェックボックス）"""

    def test_incomplete_task(self):
        xml = """
        <ac:task-list>
          <ac:task>
            <ac:task-id>1</ac:task-id>
            <ac:task-status>incomplete</ac:task-status>
            <ac:task-body>未完了タスク</ac:task-body>
          </ac:task>
        </ac:task-list>
        """
        result = convert(xml)
        assert result[0]["type"] == "to_do"
        assert result[0]["to_do"]["checked"] is False
        assert result[0]["to_do"]["rich_text"][0]["text"]["content"] == "未完了タスク"

    def test_complete_task(self):
        xml = """
        <ac:task-list>
          <ac:task>
            <ac:task-id>1</ac:task-id>
            <ac:task-status>complete</ac:task-status>
            <ac:task-body>完了タスク</ac:task-body>
          </ac:task>
        </ac:task-list>
        """
        result = convert(xml)
        assert result[0]["to_do"]["checked"] is True

    def test_multiple_tasks(self):
        xml = """
        <ac:task-list>
          <ac:task>
            <ac:task-id>1</ac:task-id>
            <ac:task-status>complete</ac:task-status>
            <ac:task-body>タスク1</ac:task-body>
          </ac:task>
          <ac:task>
            <ac:task-id>2</ac:task-id>
            <ac:task-status>incomplete</ac:task-status>
            <ac:task-body>タスク2</ac:task-body>
          </ac:task>
        </ac:task-list>
        """
        result = convert(xml)
        assert len(result) == 2
        assert result[0]["to_do"]["checked"] is True
        assert result[1]["to_do"]["checked"] is False
