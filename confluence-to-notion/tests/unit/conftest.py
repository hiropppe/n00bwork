import pytest
from confluence_to_notion.converter.parser import parse_storage_xml
from confluence_to_notion.converter.builder import build_notion_blocks

_NS = 'xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/" xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/"'


def convert(xml_snippet: str) -> list[dict]:
    """XMLスニペットをNotion Block JSONに変換するショートカット"""
    full_xml = f"<root {_NS}>{xml_snippet}</root>"
    nodes = parse_storage_xml(full_xml)
    return build_notion_blocks(nodes)
