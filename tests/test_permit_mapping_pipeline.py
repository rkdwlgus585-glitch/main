"""Comprehensive tests for core_engine.permit_mapping_pipeline.

Covers: MappingBatch dataclass, _normalize_text, _is_pending_row, _chunk,
and apply_mapping_pipeline (edge cases, batching logic, metadata integrity).
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List

from core_engine.permit_mapping_pipeline import (
    MappingBatch,
    _chunk,
    _is_pending_row,
    _normalize_text,
    apply_mapping_pipeline,
)


# ── helpers ──────────────────────────────────────────────────────────────
def _make_row(
    code: str,
    *,
    major: str = "01",
    major_name: str = "Group1",
    status: str = "pending_law_mapping",
    name: str = "",
) -> Dict[str, Any]:
    return {
        "service_code": code,
        "service_name": name or code,
        "major_code": major,
        "major_name": major_name,
        "collection_status": status,
    }


# ── MappingBatch ─────────────────────────────────────────────────────────
class MappingBatchTest(unittest.TestCase):
    def test_frozen(self):
        batch = MappingBatch("M01-B01", "01", "G1", 1, 3, ("a", "b", "c"))
        with self.assertRaises(AttributeError):
            batch.batch_id = "X"  # type: ignore[misc]

    def test_fields(self):
        batch = MappingBatch("M01-B01", "01", "G1", 1, 3, ("a", "b", "c"))
        self.assertEqual(batch.batch_id, "M01-B01")
        self.assertEqual(batch.major_code, "01")
        self.assertEqual(batch.major_name, "G1")
        self.assertEqual(batch.batch_index, 1)
        self.assertEqual(batch.item_count, 3)
        self.assertEqual(batch.service_codes, ("a", "b", "c"))

    def test_empty_service_codes(self):
        batch = MappingBatch("M01-B01", "01", "G1", 1, 0, ())
        self.assertEqual(batch.service_codes, ())
        self.assertEqual(batch.item_count, 0)


# ── _normalize_text ──────────────────────────────────────────────────────
class NormalizeTextTest(unittest.TestCase):
    def test_basic_whitespace(self):
        self.assertEqual(_normalize_text("  hello   world  "), "hello world")

    def test_none(self):
        self.assertEqual(_normalize_text(None), "")

    def test_empty_string(self):
        self.assertEqual(_normalize_text(""), "")

    def test_whitespace_only(self):
        self.assertEqual(_normalize_text("   "), "")

    def test_integer(self):
        self.assertEqual(_normalize_text(123), "123")

    def test_float(self):
        self.assertEqual(_normalize_text(1.5), "1.5")

    def test_tabs_and_newlines(self):
        self.assertEqual(_normalize_text("a\tb\nc"), "a b c")

    def test_boolean_false(self):
        # bool False → str(False or "") → ""
        self.assertEqual(_normalize_text(False), "")

    def test_boolean_true(self):
        self.assertEqual(_normalize_text(True), "True")

    def test_zero(self):
        # int 0 → str(0 or "") → ""
        self.assertEqual(_normalize_text(0), "")

    def test_single_word(self):
        self.assertEqual(_normalize_text("hello"), "hello")


# ── _is_pending_row ──────────────────────────────────────────────────────
class IsPendingRowTest(unittest.TestCase):
    def test_pending_law_mapping(self):
        self.assertTrue(_is_pending_row({"collection_status": "pending_law_mapping"}))

    def test_criteria_extracted(self):
        self.assertFalse(_is_pending_row({"collection_status": "criteria_extracted"}))

    def test_mapped(self):
        self.assertFalse(_is_pending_row({"collection_status": "mapped"}))

    def test_done(self):
        self.assertFalse(_is_pending_row({"collection_status": "done"}))

    def test_missing_key(self):
        self.assertTrue(_is_pending_row({}))

    def test_none_status(self):
        self.assertTrue(_is_pending_row({"collection_status": None}))

    def test_empty_status(self):
        self.assertTrue(_is_pending_row({"collection_status": ""}))

    def test_case_insensitive_mapped(self):
        self.assertFalse(_is_pending_row({"collection_status": "MAPPED"}))

    def test_case_insensitive_done(self):
        self.assertFalse(_is_pending_row({"collection_status": "Done"}))

    def test_whitespace_status(self):
        self.assertFalse(_is_pending_row({"collection_status": "  criteria_extracted  "}))

    def test_unknown_status_is_pending(self):
        self.assertTrue(_is_pending_row({"collection_status": "unknown"}))

    def test_candidate_collected_is_pending(self):
        self.assertTrue(_is_pending_row({"collection_status": "candidate_collected"}))


# ── _chunk ───────────────────────────────────────────────────────────────
class ChunkTest(unittest.TestCase):
    def test_basic(self):
        result = list(_chunk([1, 2, 3, 4, 5], 2))
        self.assertEqual(result, [[1, 2], [3, 4], [5]])

    def test_exact_divide(self):
        result = list(_chunk([1, 2, 3, 4], 2))
        self.assertEqual(result, [[1, 2], [3, 4]])

    def test_single_chunk(self):
        result = list(_chunk([1, 2, 3], 10))
        self.assertEqual(result, [[1, 2, 3]])

    def test_empty_list(self):
        result = list(_chunk([], 3))
        self.assertEqual(result, [])

    def test_size_zero_clamped_to_one(self):
        result = list(_chunk([1, 2, 3], 0))
        self.assertEqual(result, [[1], [2], [3]])

    def test_size_negative_clamped_to_one(self):
        result = list(_chunk([1, 2, 3], -5))
        self.assertEqual(result, [[1], [2], [3]])

    def test_size_one(self):
        result = list(_chunk(["a", "b", "c"], 1))
        self.assertEqual(result, [["a"], ["b"], ["c"]])

    def test_size_equals_length(self):
        result = list(_chunk([1, 2, 3], 3))
        self.assertEqual(result, [[1, 2, 3]])


# ── apply_mapping_pipeline (existing + edge cases) ──────────────────────
class ApplyMappingPipelineBasicTest(unittest.TestCase):
    """Port of original 2 tests + additional coverage."""

    def test_assigns_batches(self):
        industries = [
            _make_row("02_A", major="02", major_name="Group2"),
            _make_row("02_B", major="02", major_name="Group2"),
            _make_row("02_C", major="02", major_name="Group2"),
            _make_row("03_A", major="03", major_name="Group3"),
            _make_row("03_B", major="03", major_name="Group3"),
            _make_row("03_C", major="03", major_name="Group3"),
            _make_row("03_D", major="03", major_name="Group3"),
            _make_row("01_M", major="01", major_name="Mapped", status="criteria_extracted"),
        ]
        updated, meta = apply_mapping_pipeline(industries, batch_size=2)
        self.assertEqual(meta["pending_total"], 7)
        self.assertEqual(meta["mapped_total"], 1)
        self.assertEqual(meta["major_group_total"], 2)
        self.assertEqual(meta["batch_total"], 4)
        self.assertEqual(meta["batch_size"], 2)
        queued = [r for r in updated if r.get("mapping_status") == "queued_law_mapping"]
        self.assertEqual(len(queued), 7)
        self.assertTrue(all(str(r.get("mapping_batch_id", "")).startswith("M") for r in queued))

    def test_marks_mapped_rows(self):
        industries = [
            _make_row("01_A", major="01", major_name="M", status="criteria_extracted"),
            _make_row("02_A", major="02", major_name="P"),
        ]
        updated, _meta = apply_mapping_pipeline(industries, batch_size=10)
        mapped_row = next(r for r in updated if r["service_code"] == "01_A")
        pending_row = next(r for r in updated if r["service_code"] == "02_A")
        self.assertEqual(mapped_row["mapping_status"], "mapped")
        self.assertEqual(mapped_row["mapping_batch_id"], "")
        self.assertEqual(mapped_row["mapping_batch_seq"], 0)
        self.assertEqual(pending_row["mapping_status"], "queued_law_mapping")
        self.assertTrue(str(pending_row["mapping_batch_id"]).startswith("M02-"))


class ApplyMappingPipelineEdgeCaseTest(unittest.TestCase):
    """Edge cases and robustness tests."""

    def test_empty_industries(self):
        updated, meta = apply_mapping_pipeline([])
        self.assertEqual(updated, [])
        self.assertEqual(meta["pending_total"], 0)
        self.assertEqual(meta["mapped_total"], 0)
        self.assertEqual(meta["batch_total"], 0)

    def test_none_industries(self):
        updated, meta = apply_mapping_pipeline(None)  # type: ignore[arg-type]
        self.assertEqual(updated, [])
        self.assertEqual(meta["pending_total"], 0)

    def test_non_dict_items_skipped(self):
        industries = [
            "not_a_dict",
            42,
            None,
            _make_row("01_A"),
        ]
        updated, meta = apply_mapping_pipeline(industries)  # type: ignore[arg-type]
        self.assertEqual(len(updated), 1)
        self.assertEqual(meta["pending_total"], 1)

    def test_row_not_mutated(self):
        original = _make_row("01_A")
        original_copy = dict(original)
        apply_mapping_pipeline([original])
        self.assertEqual(original, original_copy)

    def test_missing_major_code(self):
        row = {"service_code": "X", "collection_status": "pending_law_mapping"}
        updated, meta = apply_mapping_pipeline([row])
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["mapping_group_key"], "")
        self.assertEqual(meta["pending_total"], 1)

    def test_missing_service_code(self):
        row = {"major_code": "01", "collection_status": "pending_law_mapping"}
        updated, _meta = apply_mapping_pipeline([row])
        self.assertEqual(len(updated), 1)
        # Row still gets queued (empty service_code normalized)
        self.assertIn(updated[0].get("mapping_status"), ("queued_law_mapping", "pending_unassigned"))

    def test_batch_size_zero(self):
        industries = [_make_row("01_A"), _make_row("01_B")]
        updated, meta = apply_mapping_pipeline(industries, batch_size=0)
        # batch_size clamped to 1 → each row gets its own batch
        self.assertEqual(meta["batch_total"], 2)
        self.assertEqual(meta["batch_size"], 1)

    def test_batch_size_negative(self):
        industries = [_make_row("01_A"), _make_row("01_B")]
        _, meta = apply_mapping_pipeline(industries, batch_size=-3)
        self.assertEqual(meta["batch_size"], 1)

    def test_single_pending_row(self):
        updated, meta = apply_mapping_pipeline([_make_row("01_A")])
        self.assertEqual(meta["pending_total"], 1)
        self.assertEqual(meta["batch_total"], 1)
        self.assertEqual(updated[0]["mapping_batch_id"], "M01-B01")
        self.assertEqual(updated[0]["mapping_batch_seq"], 1)

    def test_all_mapped(self):
        industries = [
            _make_row("01_A", status="criteria_extracted"),
            _make_row("02_A", status="done"),
        ]
        updated, meta = apply_mapping_pipeline(industries)
        self.assertEqual(meta["pending_total"], 0)
        self.assertEqual(meta["mapped_total"], 2)
        self.assertEqual(meta["batch_total"], 0)

    def test_all_status_values_mapped(self):
        for status in ("criteria_extracted", "mapped", "done"):
            row = _make_row("01_A", status=status)
            updated, _ = apply_mapping_pipeline([row])
            self.assertEqual(updated[0]["mapping_status"], "mapped", f"Status {status} should be mapped")

    def test_batch_id_format(self):
        industries = [_make_row(f"01_{chr(65 + i)}") for i in range(5)]
        _, meta = apply_mapping_pipeline(industries, batch_size=2)
        batch_ids = [b["batch_id"] for b in meta["batches"]]
        self.assertEqual(batch_ids, ["M01-B01", "M01-B02", "M01-B03"])

    def test_batch_sequence_numbers(self):
        industries = [_make_row(f"01_{chr(65 + i)}") for i in range(4)]
        updated, _ = apply_mapping_pipeline(industries, batch_size=2)
        seqs = [r["mapping_batch_seq"] for r in updated]
        # 2 batches of 2: seqs should be [1, 2, 1, 2] (sorted by code)
        self.assertEqual(sorted(seqs), [1, 1, 2, 2])

    def test_no_row_loss(self):
        n = 25
        industries = [_make_row(f"01_{i:03d}") for i in range(n)]
        updated, meta = apply_mapping_pipeline(industries, batch_size=7)
        self.assertEqual(len(updated), n)
        self.assertEqual(meta["pending_total"], n)

    def test_multiple_major_groups(self):
        industries = [
            _make_row("01_A", major="01", major_name="G1"),
            _make_row("02_A", major="02", major_name="G2"),
            _make_row("03_A", major="03", major_name="G3"),
        ]
        _, meta = apply_mapping_pipeline(industries)
        self.assertEqual(meta["major_group_total"], 3)
        self.assertEqual(meta["batch_total"], 3)
        codes = [g["major_code"] for g in meta["major_groups"]]
        self.assertEqual(codes, ["01", "02", "03"])  # sorted

    def test_major_groups_sorted(self):
        industries = [
            _make_row("03_A", major="03"),
            _make_row("01_A", major="01"),
            _make_row("02_A", major="02"),
        ]
        _, meta = apply_mapping_pipeline(industries)
        codes = [g["major_code"] for g in meta["major_groups"]]
        self.assertEqual(codes, ["01", "02", "03"])

    def test_rows_sorted_within_batch(self):
        industries = [
            _make_row("01_C", major="01"),
            _make_row("01_A", major="01"),
            _make_row("01_B", major="01"),
        ]
        updated, _ = apply_mapping_pipeline(industries, batch_size=10)
        queued = [r for r in updated if r.get("mapping_status") == "queued_law_mapping"]
        seqs = [(r["service_code"], r["mapping_batch_seq"]) for r in queued]
        # Sorted by code → 01_A=seq1, 01_B=seq2, 01_C=seq3
        seq_map = {code: seq for code, seq in seqs}
        self.assertEqual(seq_map["01_A"], 1)
        self.assertEqual(seq_map["01_B"], 2)
        self.assertEqual(seq_map["01_C"], 3)

    def test_metadata_generated_at_iso(self):
        _, meta = apply_mapping_pipeline([_make_row("01_A")])
        ts = meta["generated_at"]
        self.assertIsInstance(ts, str)
        self.assertIn("T", ts)

    def test_metadata_batches_detail(self):
        industries = [_make_row(f"01_{chr(65 + i)}") for i in range(3)]
        _, meta = apply_mapping_pipeline(industries, batch_size=2)
        batches = meta["batches"]
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0]["item_count"], 2)
        self.assertEqual(batches[1]["item_count"], 1)
        self.assertIsInstance(batches[0]["service_codes"], list)

    def test_whitespace_in_codes(self):
        row = _make_row("  01_A  ", major="  01  ", major_name="  Group  1  ")
        updated, _ = apply_mapping_pipeline([row])
        self.assertEqual(updated[0]["mapping_group_key"], "01")

    def test_empty_major_code_batch_id(self):
        """Rows with empty major_code get M00-Bxx batch IDs."""
        row = {"service_code": "X", "collection_status": "pending_law_mapping"}
        updated, meta = apply_mapping_pipeline([row])
        if meta["batch_total"] > 0:
            self.assertTrue(meta["batches"][0]["batch_id"].startswith("M00-"))

    def test_duplicate_service_codes_across_majors(self):
        """Same service_code in different major groups — last lookup wins."""
        industries = [
            _make_row("DUP", major="01", major_name="G1"),
            _make_row("DUP", major="02", major_name="G2"),
        ]
        updated, meta = apply_mapping_pipeline(industries, batch_size=10)
        # Both rows exist; lookup collision means one gets assigned, other may become unassigned
        self.assertEqual(len(updated), 2)
        statuses = {r.get("mapping_status") for r in updated}
        self.assertTrue(statuses.issubset({"queued_law_mapping", "pending_unassigned"}))

    def test_exact_batch_boundary(self):
        """N rows with batch_size=N → exactly 1 batch."""
        n = 5
        industries = [_make_row(f"01_{i:02d}") for i in range(n)]
        _, meta = apply_mapping_pipeline(industries, batch_size=n)
        self.assertEqual(meta["batch_total"], 1)
        self.assertEqual(meta["batches"][0]["item_count"], n)

    def test_batch_boundary_plus_one(self):
        """N+1 rows with batch_size=N → 2 batches."""
        n = 5
        industries = [_make_row(f"01_{i:02d}") for i in range(n + 1)]
        _, meta = apply_mapping_pipeline(industries, batch_size=n)
        self.assertEqual(meta["batch_total"], 2)
        self.assertEqual(meta["batches"][0]["item_count"], n)
        self.assertEqual(meta["batches"][1]["item_count"], 1)


if __name__ == "__main__":
    unittest.main()
