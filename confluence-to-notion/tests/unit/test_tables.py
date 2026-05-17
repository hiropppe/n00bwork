"""テストリスト 3-19〜3-25: テーブルの変換テスト"""

import pytest
from tests.unit.conftest import convert


class TestBasicTable:
    """3-19: 基本テーブル"""

    def test_simple_2x2_table(self):
        xml = """
        <table>
          <tbody>
            <tr><td>A1</td><td>A2</td></tr>
            <tr><td>B1</td><td>B2</td></tr>
          </tbody>
        </table>
        """
        result = convert(xml)
        assert result[0]["type"] == "table"
        table = result[0]["table"]
        assert table["table_width"] == 2
        assert table["has_column_header"] is False
        rows = table["children"]
        assert len(rows) == 2
        assert rows[0]["type"] == "table_row"

    def test_table_cell_content(self):
        xml = """
        <table>
          <tbody>
            <tr><td>セル内容</td></tr>
          </tbody>
        </table>
        """
        result = convert(xml)
        rows = result[0]["table"]["children"]
        cells = rows[0]["table_row"]["cells"]
        assert cells[0][0]["text"]["content"] == "セル内容"


class TestTableWithHeader:
    """3-22: ヘッダー行"""

    def test_header_row_with_th(self):
        xml = """
        <table>
          <tbody>
            <tr><th>名前</th><th>値</th></tr>
            <tr><td>foo</td><td>bar</td></tr>
          </tbody>
        </table>
        """
        result = convert(xml)
        assert result[0]["table"]["has_row_header"] is True

    def test_no_header_with_td_only(self):
        xml = """
        <table>
          <tbody>
            <tr><td>A</td><td>B</td></tr>
          </tbody>
        </table>
        """
        result = convert(xml)
        assert result[0]["table"]["has_row_header"] is False


class TestTableCellContent:
    """3-24: セル内のリッチテキスト"""

    def test_cell_with_bold_text(self):
        xml = """
        <table>
          <tbody>
            <tr><td><strong>太字セル</strong></td></tr>
          </tbody>
        </table>
        """
        result = convert(xml)
        cells = result[0]["table"]["children"][0]["table_row"]["cells"]
        assert cells[0][0]["annotations"]["bold"] is True
