"""ページ単位の移行ロジック"""

from .client.confluence import ConfluenceClient
from .client.notion import NotionClient
from .converter.parser import parse_storage_xml
from .converter.builder import build_notion_blocks


class MigrationRunner:
    def __init__(self, confluence: ConfluenceClient, notion: NotionClient):
        self._confluence = confluence
        self._notion = notion

    def migrate_page(self, confluence_page_id: str, notion_parent_page_id: str) -> str:
        """Confluence ページを Notion に移行し、作成された Notion ページIDを返す"""
        page = self._confluence._client.get_page_by_id(
            confluence_page_id, expand="body.storage,title"
        )
        title = page["title"]
        storage_xml = page["body"]["storage"]["value"]

        nodes = parse_storage_xml(storage_xml)
        blocks = build_notion_blocks(nodes)

        return self._notion.create_page(
            parent_page_id=notion_parent_page_id,
            title=title,
            blocks=blocks,
        )
