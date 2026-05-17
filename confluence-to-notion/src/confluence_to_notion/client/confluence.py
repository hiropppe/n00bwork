"""Confluence DC API ラッパー（テスト用のページ作成・削除を含む）"""

import os
from atlassian import Confluence


class ConfluenceClient:
    def __init__(self):
        url = os.environ["CONFLUENCE_DC_URL"]
        pat = os.environ["CONFLUENCE_DC_PAT"]
        self._client = Confluence(url=url, token=pat)

    def get_page_storage_xml(self, page_id: str) -> str:
        page = self._client.get_page_by_id(page_id, expand="body.storage")
        return page["body"]["storage"]["value"]

    def create_test_page(self, space: str, title: str, storage_xml: str) -> str:
        """Storage Format XML でテストページを作成し、ページIDを返す"""
        result = self._client.create_page(
            space=space,
            title=title,
            body=storage_xml,
            representation="storage",
        )
        return str(result["id"])

    def delete_page(self, page_id: str) -> None:
        self._client.remove_page(page_id)

    def get_page_ancestors(self, page_id: str) -> list[dict]:
        page = self._client.get_page_by_id(page_id, expand="ancestors")
        return page.get("ancestors", [])
