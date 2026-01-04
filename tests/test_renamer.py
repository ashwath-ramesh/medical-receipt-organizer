"""Tests for renamer module."""

import pytest

from receipt_organizer.models import ReceiptData
from receipt_organizer.renamer import FileRenamer


class TestFileRenamer:
    def test_generate_new_name_complete_data(self, sample_receipt_data):
        renamer = FileRenamer()
        result = renamer.generate_new_name(sample_receipt_data, ".pdf")
        assert result == "2024-01-15_CvsPharmacy_JohnDoe_USD45.99.pdf"

    def test_generate_new_name_missing_date(self):
        renamer = FileRenamer()
        data = ReceiptData(
            is_medical_receipt=True,
            provider="Walgreens",
            patient="Jane",
            date=None,
            amount=10.00,
        )
        result = renamer.generate_new_name(data, ".pdf")
        assert result.startswith("REVIEW_")

    def test_generate_new_name_whole_number_amount(self):
        renamer = FileRenamer()
        data = ReceiptData(
            is_medical_receipt=True,
            provider="Clinic",
            patient="Test",
            date="2024-06-01",
            amount=100.0,
        )
        result = renamer.generate_new_name(data, ".pdf")
        assert "USD100" in result
        assert "USD100.00" not in result

    def test_sanitize_removes_special_chars(self):
        renamer = FileRenamer()
        assert renamer.sanitize("Dr. Smith's Clinic!") == "DrSmithsClinic"

    def test_sanitize_handles_none(self):
        renamer = FileRenamer()
        assert renamer.sanitize(None) == "UNKNOWN"

    def test_sanitize_truncates_long_names(self):
        renamer = FileRenamer()
        long_name = "A" * 50
        result = renamer.sanitize(long_name)
        assert len(result) == 30

    def test_resolve_conflict_no_conflict(self, tmp_path):
        renamer = FileRenamer()
        result = renamer.resolve_conflict(tmp_path, "test.pdf")
        assert result == "test.pdf"

    def test_resolve_conflict_creates_unique_names(self, tmp_path):
        renamer = FileRenamer()
        (tmp_path / "test.pdf").touch()
        result = renamer.resolve_conflict(tmp_path, "test.pdf")
        assert result == "test_1.pdf"

    def test_resolve_conflict_increments_suffix(self, tmp_path):
        renamer = FileRenamer()
        (tmp_path / "test.pdf").touch()
        (tmp_path / "test_1.pdf").touch()
        result = renamer.resolve_conflict(tmp_path, "test.pdf")
        assert result == "test_2.pdf"

    def test_execute_rename_moves_file(self, tmp_path):
        renamer = FileRenamer()
        source = tmp_path / "old.pdf"
        source.touch()
        result = renamer.execute_rename(source, "new.pdf")
        assert result == tmp_path / "new.pdf"
        assert result.exists()
        assert not source.exists()

    def test_execute_rename_blocks_path_traversal(self, tmp_path):
        renamer = FileRenamer()
        source = tmp_path / "test.pdf"
        source.touch()
        with pytest.raises(ValueError, match="Path traversal"):
            renamer.execute_rename(source, "../malicious.pdf")

    def test_format_amount_with_decimals(self):
        renamer = FileRenamer()
        assert renamer.format_amount(45.99) == "USD45.99"

    def test_format_amount_whole_number(self):
        renamer = FileRenamer()
        assert renamer.format_amount(100.0) == "USD100"

    def test_format_amount_none(self):
        renamer = FileRenamer()
        assert renamer.format_amount(None) == "UNKNOWN"

    def test_format_amount_different_currency(self):
        renamer = FileRenamer()
        assert renamer.format_amount(50.0, "SGD") == "SGD50"
