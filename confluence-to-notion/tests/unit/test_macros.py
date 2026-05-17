"""テストリスト カテゴリ6: マクロの変換テスト"""

import pytest
from tests.unit.conftest import convert


class TestInfoPanelMacros:
    """6-1〜6-5: 情報パネル系マクロ → callout"""

    @pytest.mark.parametrize("macro_name,expected_color,expected_emoji", [
        ("info",    "blue_background",   "ℹ️"),
        ("tip",     "green_background",  "💡"),
        ("note",    "yellow_background", "⚠️"),
        ("warning", "red_background",    "🚨"),
        ("panel",   "gray_background",   "📋"),
    ])
    def test_panel_to_callout(self, macro_name, expected_color, expected_emoji):
        xml = f"""
        <ac:structured-macro ac:name="{macro_name}">
          <ac:rich-text-body><p>本文テキスト</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "callout"
        callout = result[0]["callout"]
        assert callout["color"] == expected_color
        assert callout["icon"]["emoji"] == expected_emoji

    def test_info_with_body_text(self):
        xml = """
        <ac:structured-macro ac:name="info">
          <ac:rich-text-body><p>詳細情報がここに入ります。</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        callout = result[0]["callout"]
        assert callout["rich_text"][0]["text"]["content"] == "詳細情報がここに入ります。"

    def test_warning_with_nested_content(self):
        xml = """
        <ac:structured-macro ac:name="warning">
          <ac:rich-text-body>
            <p>警告タイトル</p>
            <p>補足説明</p>
          </ac:rich-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "callout"
        # 2段落目以降は children に入る
        callout = result[0]["callout"]
        assert callout["rich_text"][0]["text"]["content"] == "警告タイトル"
        assert len(callout["children"]) >= 1


class TestExpandMacro:
    """6-6: expand マクロ → toggle"""

    def test_expand_to_toggle(self):
        xml = """
        <ac:structured-macro ac:name="expand">
          <ac:parameter ac:name="title">クリックして展開</ac:parameter>
          <ac:rich-text-body><p>折りたたまれたコンテンツ</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "toggle"
        toggle = result[0]["toggle"]
        assert toggle["rich_text"][0]["text"]["content"] == "クリックして展開"
        assert toggle["children"][0]["type"] == "paragraph"

    def test_expand_without_title(self):
        """タイトルなしの expand → デフォルトタイトル"""
        xml = """
        <ac:structured-macro ac:name="expand">
          <ac:rich-text-body><p>内容</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "toggle"
        # タイトルがデフォルト文字列になっていること
        assert result[0]["toggle"]["rich_text"][0]["text"]["content"] != ""


class TestCodeMacro:
    """コードブロックマクロ（ac:name="code"）の変換テスト"""

    def test_code_macro_is_code_block(self):
        xml = """
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">python</ac:parameter>
          <ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "code"


class TestUnsupportedMacros:
    """✕困難マクロ → 警告 callout"""

    @pytest.mark.parametrize("macro_name", [
        "toc", "pagetree", "livesearch", "taskreport",
        "page-index", "recently-updated", "breadcrumbs",
        "anchor", "excerpt",
    ])
    def test_unsupported_macro_becomes_warning_callout(self, macro_name):
        xml = f'<ac:structured-macro ac:name="{macro_name}"/>'
        result = convert(xml)
        assert result[0]["type"] == "callout"
        callout = result[0]["callout"]
        assert callout["color"] == "orange_background"
        assert "移行不可" in callout["rich_text"][0]["text"]["content"]

    def test_toc_warning_message_contains_macro_name(self):
        result = convert('<ac:structured-macro ac:name="toc"/>')
        msg = result[0]["callout"]["rich_text"][0]["text"]["content"]
        assert "toc" in msg.lower()


class TestWidgetMacro:
    """6-25: widget マクロ → embed"""

    def test_widget_with_url_becomes_embed(self):
        xml = """
        <ac:structured-macro ac:name="widget">
          <ac:parameter ac:name="url">https://www.youtube.com/watch?v=test</ac:parameter>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "embed"
        assert result[0]["embed"]["url"] == "https://www.youtube.com/watch?v=test"


class TestIncludeMacro:
    """6-13: include マクロ → 警告 callout"""

    def test_include_macro_becomes_warning(self):
        xml = """
        <ac:structured-macro ac:name="include">
          <ac:parameter ac:name=""><ri:page ri:content-title="参照ページ名"/></ac:parameter>
        </ac:structured-macro>
        """
        result = convert(xml)
        assert result[0]["type"] == "callout"
        assert result[0]["callout"]["color"] == "orange_background"
