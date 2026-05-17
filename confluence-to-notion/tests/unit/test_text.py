"""テストリスト 3-1〜3-10: 基本テキスト書式の変換テスト"""

import pytest
from tests.unit.conftest import convert


class TestHeadings:
    """3-1: 見出し H1〜H3"""

    def test_h1(self):
        result = convert("<h1>見出し1</h1>")
        assert result[0]["type"] == "heading_1"
        assert result[0]["heading_1"]["rich_text"][0]["text"]["content"] == "見出し1"

    def test_h2(self):
        result = convert("<h2>見出し2</h2>")
        assert result[0]["type"] == "heading_2"

    def test_h3(self):
        result = convert("<h3>見出し3</h3>")
        assert result[0]["type"] == "heading_3"

    def test_h4_falls_back_to_bold_paragraph(self):
        """3-2: H4 は Notion 非対応 → 太字 paragraph"""
        result = convert("<h4>見出し4</h4>")
        assert result[0]["type"] == "paragraph"
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True

    def test_h5_falls_back_to_bold_paragraph(self):
        """3-2: H5 も同様"""
        result = convert("<h5>見出し5</h5>")
        assert result[0]["type"] == "paragraph"
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True

    def test_h6_falls_back_to_bold_paragraph(self):
        """3-2: H6 も同様"""
        result = convert("<h6>見出し6</h6>")
        assert result[0]["type"] == "paragraph"
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True


class TestInlineAnnotations:
    """3-3: 太字・斜体"""

    def test_bold(self):
        result = convert("<p><strong>太字</strong></p>")
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["text"]["content"] == "太字"
        assert rt["annotations"]["bold"] is True

    def test_italic(self):
        result = convert("<p><em>斜体</em></p>")
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["annotations"]["italic"] is True

    def test_bold_alias_b(self):
        result = convert("<p><b>太字</b></p>")
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["bold"] is True

    def test_italic_alias_i(self):
        result = convert("<p><i>斜体</i></p>")
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["italic"] is True

    def test_mixed_bold_italic(self):
        """3-3: 太字と斜体の組み合わせ"""
        result = convert("<p><strong><em>太字斜体</em></strong></p>")
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["annotations"]["bold"] is True
        assert rt["annotations"]["italic"] is True

    def test_strikethrough(self):
        """3-5: 取り消し線"""
        result = convert("<p><s>取り消し線</s></p>")
        assert result[0]["paragraph"]["rich_text"][0]["annotations"]["strikethrough"] is True

    def test_underline_becomes_plain_text(self):
        """3-4: 下線は Notion 非対応 → プレーンテキスト（アノテーション落とし）"""
        result = convert("<p><u>下線テキスト</u></p>")
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["text"]["content"] == "下線テキスト"
        assert rt["annotations"]["bold"] is False
        assert rt["annotations"]["italic"] is False
        assert rt["annotations"]["underline"] is False

    def test_inline_code(self):
        """3-9: コードインライン"""
        result = convert("<p><code>inline_code()</code></p>")
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["annotations"]["code"] is True
        assert rt["text"]["content"] == "inline_code()"

    def test_superscript_as_plain(self):
        """3-8: 上付き文字（Notion に専用アノテーションなし → プレーンで出力）"""
        result = convert("<p>x<sup>2</sup></p>")
        texts = [rt["text"]["content"] for rt in result[0]["paragraph"]["rich_text"]]
        assert "2" in texts

    def test_subscript_as_plain(self):
        """3-8: 下付き文字"""
        result = convert("<p>H<sub>2</sub>O</p>")
        texts = [rt["text"]["content"] for rt in result[0]["paragraph"]["rich_text"]]
        assert "2" in texts

    def test_mixed_text_and_bold(self):
        """プレーンテキストと太字が混在する段落"""
        result = convert("<p>通常テキスト<strong>太字</strong>通常</p>")
        rts = result[0]["paragraph"]["rich_text"]
        plain_texts = [rt["text"]["content"] for rt in rts]
        assert "通常テキスト" in plain_texts
        assert "太字" in plain_texts
        bold_rt = next(rt for rt in rts if rt["text"]["content"] == "太字")
        assert bold_rt["annotations"]["bold"] is True


class TestExternalLink:
    """4-4: 外部 URL リンク"""

    def test_external_link(self):
        result = convert('<p><a href="https://example.com">リンクテキスト</a></p>')
        rt = result[0]["paragraph"]["rich_text"][0]
        assert rt["text"]["content"] == "リンクテキスト"
        assert rt["text"]["link"]["url"] == "https://example.com"


class TestQuoteAndDivider:
    """3-26: 引用ブロック / 3-27: 水平線"""

    def test_blockquote(self):
        result = convert("<blockquote>引用テキスト</blockquote>")
        assert result[0]["type"] == "quote"
        assert result[0]["quote"]["rich_text"][0]["text"]["content"] == "引用テキスト"

    def test_hr_becomes_divider(self):
        result = convert("<hr/>")
        assert result[0]["type"] == "divider"
