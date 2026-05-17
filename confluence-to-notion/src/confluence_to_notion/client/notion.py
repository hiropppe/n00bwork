"""Notion API ラッパー"""

import os
from notion_client import Client


class NotionClient:
    def __init__(self):
        self._client = Client(auth=os.environ["NOTION_API_KEY"])

    def create_page(self, parent_page_id: str, title: str, blocks: list[dict]) -> str:
        """ページを作成し、ページIDを返す"""
        # Notion API は一度に100ブロックまでしか受け付けない
        first_batch = blocks[:100]
        rest = blocks[100:]

        page = self._client.pages.create(
            parent={"page_id": parent_page_id},
            properties={
                "title": {"title": [{"text": {"content": title}}]}
            },
            children=first_batch,
        )
        page_id = page["id"]

        # 100ブロックを超える場合は追加
        for i in range(0, len(rest), 100):
            self._client.blocks.children.append(
                block_id=page_id,
                children=rest[i:i + 100],
            )

        return page_id

    def get_blocks(self, page_id: str) -> list[dict]:
        """ページのブロック一覧を全件取得する（has_more 対応）"""
        blocks = []
        cursor = None
        while True:
            kwargs = {"block_id": page_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._client.blocks.children.list(**kwargs)
            blocks.extend(response["results"])
            if not response["has_more"]:
                break
            cursor = response["next_cursor"]
        return blocks

    def delete_page(self, page_id: str) -> None:
        """ページをアーカイブ（Notion の削除はアーカイブ）"""
        self._client.pages.update(page_id=page_id, archived=True)
