from __future__ import annotations

from jdsf.ids import couple_id, judge_id, person_id, round_id


class TestPersonId:
    def test_deterministic(self):
        assert person_id("福原 聖太") == person_id("福原 聖太")

    def test_different_inputs_differ(self):
        assert person_id("福原 聖太") != person_id("土屋 海音")

    def test_within_bigint_positive_range(self):
        # DuckDB BIGINT 正値範囲（2^63 - 1）以下
        assert 0 <= person_id("foo") <= 0x7FFFFFFFFFFFFFFF


class TestJudgeId:
    def test_independent_namespace_from_person(self):
        # 同じ正規化名でも judge と person で空間を分離（万一の同名混在対策）
        assert person_id("水本 慶子") != judge_id("水本 慶子")


class TestCoupleId:
    def test_order_matters(self):
        # リーダー・パートナーの役割が逆になれば別カップル
        a = person_id("A")
        b = person_id("B")
        assert couple_id(a, b) != couple_id(b, a)

    def test_deterministic(self):
        a = person_id("A")
        b = person_id("B")
        assert couple_id(a, b) == couple_id(a, b)


class TestRoundId:
    def test_seq_changes_id(self):
        assert round_id("260416_03", "prelim", 1) != round_id("260416_03", "prelim", 2)

    def test_kind_changes_id(self):
        assert round_id("260416_03", "prelim", 1) != round_id("260416_03", "final", 1)
