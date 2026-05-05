from __future__ import annotations

import pytest

from jdsf.normalize import (
    UnknownDanceCode,
    normalize_dance_code,
    normalize_name,
    normalize_text,
)


class TestNormalizeText:
    def test_strips_and_collapses_whitespace(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_nfkc_fullwidth_to_halfwidth(self):
        assert normalize_text("ＡＢＣ１２３") == "ABC123"

    def test_idempotent(self):
        s = "山田 太郎"
        assert normalize_text(normalize_text(s)) == normalize_text(s)


class TestNormalizeName:
    def test_japanese_name_with_fullwidth_space(self):
        # JDSF ページは全角空白で区切られていることが多い
        assert normalize_name("福原　聖太") == "福原 聖太"

    def test_trailing_whitespace(self):
        assert normalize_name("土屋　海音      ") == "土屋 海音"


class TestNormalizeDanceCode:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("W", "W"),
            ("Ｗ", "W"),
            ("Wz", "W"),
            ("Waltz", "W"),
            ("T", "T"),
            ("Tg", "T"),
            ("Tango", "T"),
            ("V", "V"),
            ("VW", "V"),
            ("V. Waltz", "V"),
            ("(V)", "V"),  # 括弧付き
            ("F", "F"),
            ("Sf", "F"),
            ("Slowfox", "F"),
            ("Q", "Q"),
            ("Qu", "Q"),
            ("Quickstep", "Q"),
            ("S", "S"),
            ("Sa", "S"),
            ("CC", "C"),
            ("Ru", "R"),
            ("PD", "P"),
            ("Jv", "J"),
        ],
    )
    def test_known_codes(self, raw, expected):
        assert normalize_dance_code(raw) == expected

    def test_unknown_raises(self):
        with pytest.raises(UnknownDanceCode):
            normalize_dance_code("Mambo")
