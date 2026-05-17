"""E2Eテスト共通 fixture"""

import os
import time
import pytest
from dotenv import load_dotenv

from confluence_to_notion.client.confluence import ConfluenceClient
from confluence_to_notion.client.notion import NotionClient
from confluence_to_notion.migration import MigrationRunner

load_dotenv()

CONFLUENCE_TEST_SPACE = "SPC"


@pytest.fixture(scope="session")
def confluence_client():
    return ConfluenceClient()


@pytest.fixture(scope="session")
def notion_client():
    return NotionClient()


@pytest.fixture(scope="session")
def migration_runner(confluence_client, notion_client):
    return MigrationRunner(confluence_client, notion_client)


@pytest.fixture()
def migrated_notion_page(request, confluence_client, notion_client, migration_runner):
    """
    Confluenceにテストページを作成し、移行を実行して Notion ページIDを返す。
    テスト終了後に両側のページを削除する。

    使い方:
        @pytest.mark.parametrize("migrated_notion_page", [
            {"title": "テスト名", "xml": "<p>内容</p>"}
        ], indirect=True)
        def test_xxx(migrated_notion_page, notion_client):
            blocks = notion_client.get_blocks(migrated_notion_page)
            ...
    """
    xml_body = request.param["xml"]
    unique_title = f"[E2E] {request.param['title']} {int(time.time())}"

    confluence_page_id = confluence_client.create_test_page(
        space=CONFLUENCE_TEST_SPACE,
        title=unique_title,
        storage_xml=xml_body,
    )

    notion_page_id = migration_runner.migrate_page(
        confluence_page_id=confluence_page_id,
        notion_parent_page_id=os.environ["NOTION_TEST_PAGE_ID"],
    )

    yield notion_page_id

    try:
        confluence_client.delete_page(confluence_page_id)
    except Exception:
        pass
    try:
        notion_client.delete_page(notion_page_id)
    except Exception:
        pass
