"""テストリスト 2-1〜2-4: レイアウト（カラム）の変換テスト"""

from tests.unit.conftest import convert


class TestSingleColumnLayout:
    """2-1: 1カラムレイアウトはcolumn_listを作らずフラットに展開"""

    def test_single_column_flattened(self):
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="single">
            <ac:layout-cell>
              <p>テキスト</p>
            </ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        assert result[0]["type"] == "paragraph"
        assert all(b["type"] != "column_list" for b in result)


class TestTwoColumnLayout:
    """2-2: 2カラムレイアウト → column_list + 2つのcolumn"""

    def test_two_equal_columns_structure(self):
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="two_equal">
            <ac:layout-cell><p>左カラム</p></ac:layout-cell>
            <ac:layout-cell><p>右カラム</p></ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        assert result[0]["type"] == "column_list"
        columns = result[0]["column_list"]["children"]
        assert len(columns) == 2
        assert columns[0]["type"] == "column"
        assert columns[1]["type"] == "column"

    def test_two_column_content(self):
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="two_equal">
            <ac:layout-cell><p>左</p></ac:layout-cell>
            <ac:layout-cell><p>右</p></ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        columns = result[0]["column_list"]["children"]
        left = columns[0]["column"]["children"]
        right = columns[1]["column"]["children"]
        assert left[0]["paragraph"]["rich_text"][0]["text"]["content"] == "左"
        assert right[0]["paragraph"]["rich_text"][0]["text"]["content"] == "右"

    def test_two_left_sidebar_becomes_two_columns(self):
        """列幅が不均等でもNotion上は均等2カラムに変換される"""
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="two_left_sidebar">
            <ac:layout-cell><p>サイドバー</p></ac:layout-cell>
            <ac:layout-cell><p>メイン</p></ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        assert result[0]["type"] == "column_list"
        assert len(result[0]["column_list"]["children"]) == 2


class TestThreeColumnLayout:
    """2-4: 3カラムレイアウト → column_list + 3つのcolumn"""

    def test_three_equal_columns(self):
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="three_equal">
            <ac:layout-cell><p>A</p></ac:layout-cell>
            <ac:layout-cell><p>B</p></ac:layout-cell>
            <ac:layout-cell><p>C</p></ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        assert result[0]["type"] == "column_list"
        assert len(result[0]["column_list"]["children"]) == 3


class TestMixedSections:
    """1カラムセクション + 2カラムセクションの混在"""

    def test_single_then_two_column(self):
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="single">
            <ac:layout-cell><p>全幅テキスト</p></ac:layout-cell>
          </ac:layout-section>
          <ac:layout-section ac:type="two_equal">
            <ac:layout-cell><p>左</p></ac:layout-cell>
            <ac:layout-cell><p>右</p></ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """
        result = convert(xml)
        assert result[0]["type"] == "paragraph"
        assert result[1]["type"] == "column_list"
        assert len(result[1]["column_list"]["children"]) == 2
