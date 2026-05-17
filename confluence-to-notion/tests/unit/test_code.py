"""テストリスト 3-11〜3-14: コードブロックの変換テスト"""

import pytest
from tests.unit.conftest import convert


class TestCodeBlock:
    """3-11: コードブロック（言語指定・シンタックスハイライト）"""

    def test_python_code_block(self):
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">python</ac:parameter>
          <ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "code"
        assert result[0]["code"]["language"] == "python"
        assert result[0]["code"]["rich_text"][0]["text"]["content"] == 'print("hello")'

    def test_javascript_code_block(self):
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">javascript</ac:parameter>
          <ac:plain-text-body><![CDATA[console.log("hi");]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["code"]["language"] == "javascript"

    def test_bash_alias_sh(self):
        """sh は shell にマッピング"""
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">sh</ac:parameter>
          <ac:plain-text-body><![CDATA[echo hello]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["code"]["language"] == "shell"

    def test_unknown_language_falls_back_to_plain_text(self):
        """3-11: Notion 非対応言語は plain text にフォールバック"""
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">cobol</ac:parameter>
          <ac:plain-text-body><![CDATA[DISPLAY "HELLO"]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["code"]["language"] == "plain text"

    def test_no_language_defaults_to_plain_text(self):
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:plain-text-body><![CDATA[some code]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["code"]["language"] == "plain text"

    def test_code_title_goes_to_caption(self):
        """3-12: タイトルは Notion の caption フィールドに移動（タイトルフィールドなし）"""
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="title">My Script</ac:parameter>
          <ac:parameter ac:name="language">bash</ac:parameter>
          <ac:plain-text-body><![CDATA[echo hello]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "code"
        caption = result[0]["code"]["caption"]
        assert caption[0]["text"]["content"] == "My Script"

    def test_multiline_code(self):
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">python</ac:parameter>
          <ac:plain-text-body><![CDATA[def foo():
    return 42]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        code_text = result[0]["code"]["rich_text"][0]["text"]["content"]
        assert "def foo():" in code_text
        assert "return 42" in code_text
