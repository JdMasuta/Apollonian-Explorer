"""Unit tests for services/serializers.py (record/row <-> API shapes)."""

from fractions import Fraction

import pytest

from core.engine.seeds import seed_from_preset, seed_from_triple
from core.engine.walk import WalkBudget, walk
from services.serializers import (
    db_word,
    record_to_api_circle,
    record_to_row,
    row_to_response,
)


def classic_records(depth=1):
    return list(walk(seed_from_preset("classic"), WalkBudget(max_depth=depth)))


class TestRecordToApiCircle:
    def test_integral_packing_exact(self):
        records = classic_records()
        seeds = {r.circle.curvature: r for r in records if r.generation == 0}

        top = record_to_api_circle(seeds[3])
        assert top["curvature"] == "3/1"
        assert top["center"] == {"x": "0/1", "y": "2/3"}
        assert top["radius"] == "1/3"
        assert top["word"] == "S3"

        bounding = record_to_api_circle(seeds[-1])
        assert bounding["curvature"] == "-1/1"
        assert bounding["radius"] == "-1/1"  # signed, legacy contract

    def test_mixed_rational_bend_irrational_center(self):
        """(1,1,1): bends are rational ints, centers are irrational.

        Regression: serialization must pick exact vs float-mirror PER
        component; keying on the curvature alone crashed with
        'argument should be a string or a Rational instance'."""
        records = list(walk(seed_from_triple(1, 1, 1), WalkBudget(max_depth=1)))
        for record in records:
            data = record_to_api_circle(record)  # must not raise
            for field in (data["curvature"], data["radius"]):
                num, denom = (int(p) for p in field.split("/"))
                assert denom != 0
            for axis in ("x", "y"):
                num, denom = (int(p) for p in data["center"][axis].split("/"))
                assert denom != 0
        # The unit bends serialize exactly
        unit = next(r for r in records if r.circle.curvature == 1)
        assert record_to_api_circle(unit)["curvature"] == "1/1"

    def test_line_rejected(self):
        from core.engine.seeds import seed_strip

        line_record = next(
            r for r in walk(seed_strip(), WalkBudget(max_depth=0)) if r.circle.is_line
        )
        with pytest.raises(ValueError, match="Lines"):
            record_to_api_circle(line_record)


class TestDbWord:
    def test_seed_words(self):
        records = classic_records(0)
        assert [db_word(r) for r in records] == ["S0", "S1", "S2", "S3"]

    def test_generated_words(self):
        records = [r for r in classic_records(2) if r.generation > 0]
        words = [db_word(r) for r in records]
        assert len(words) == len(set(words))
        assert all(w and all(ch in "0123" for ch in w) for w in words)


class TestRowRoundtrip:
    def test_row_roundtrip_exact(self):
        record = next(r for r in classic_records() if r.circle.curvature == 15)
        row = record_to_row(record, gasket_id=1)
        row.id = 42

        assert row.word == "0"
        assert row.curvature_exact == "15"
        assert row.b_f == 15.0

        response = row_to_response(row)
        assert response.curvature == "15/1"
        assert response.center == {"x": "0/1", "y": "4/15"}
        assert response.word == "0"
        assert response.id == 42

    def test_row_roundtrip_mixed(self):
        """Rational bend + irrational center row serializes per component."""
        records = list(walk(seed_from_triple(1, 1, 1), WalkBudget(max_depth=0)))
        unit = next(r for r in records if r.circle.curvature == 1 and r.y_f and r.y_f > 0.1)
        row = record_to_row(unit, gasket_id=1)
        row.id = 1

        response = row_to_response(row)
        assert response.curvature == "1/1"  # exact
        # irrational center came from the float mirror
        num, denom = (int(p) for p in response.center["y"].split("/"))
        assert abs(num / denom - unit.y_f) < 1e-8
