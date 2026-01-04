"""Tests for CLI module."""

import sys

import pytest

from receipt_organizer.cli import ProcessResult, main, process_single_file
from receipt_organizer.models import ReceiptData


class TestProcessResult:
    def test_process_result_defaults(self, tmp_path):
        result = ProcessResult(file_path=tmp_path / "test.pdf")
        assert result.data is None
        assert result.new_name is None
        assert result.error is None
        assert result.skipped_reason is None


class TestCLI:
    def test_help_displays_usage(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["receipt-organizer", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--dry-run" in captured.out
        assert "--verbose" in captured.out

    def test_invalid_directory_exits_with_error(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["receipt-organizer", "/nonexistent/path"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_not_a_directory_exits_with_error(self, tmp_path, capsys, monkeypatch):
        file_path = tmp_path / "file.txt"
        file_path.touch()
        monkeypatch.setattr(sys, "argv", ["receipt-organizer", str(file_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err.lower()

    def test_invalid_workers_exits_with_error(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["receipt-organizer", str(tmp_path), "--workers", "0"]
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "workers" in captured.err.lower()

    def test_dry_run_does_not_rename(self, tmp_path, mocker, monkeypatch):
        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")
        original_files = set(tmp_path.iterdir())

        # Mock the extractor to avoid needing Ollama
        mock_extractor = mocker.patch("receipt_organizer.cli.ReceiptExtractor")
        mock_instance = mock_extractor.return_value
        mock_instance.check_available.return_value = (True, "")

        # Mock process_files to avoid actual processing
        mocker.patch("receipt_organizer.cli.process_files", return_value=(0, 0, 0))

        monkeypatch.setattr(
            sys, "argv", ["receipt-organizer", str(tmp_path), "--dry-run", "-y"]
        )
        main()

        # Files should be unchanged
        assert set(tmp_path.iterdir()) == original_files

    def test_unrecognized_option_exits_with_error(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["receipt-organizer", "--unknown-option"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        # argparse returns 2 for unrecognized arguments
        assert exc_info.value.code == 2


class TestProcessSingleFile:
    def test_returns_error_when_file_unreadable(self, tmp_path, mocker):
        """Test process_single_file when file cannot be read."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        # Create mocks
        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = None  # Simulate read failure

        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        renamer = mocker.MagicMock(spec=FileRenamer)
        counter = {"done": 0}

        result = process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=True,
            verbose=False,
            confirm=False,
            counter=counter,
            total=1,
        )

        assert result.error == "failed to read file"
        assert counter["done"] == 1

    def test_returns_error_when_extraction_fails(self, tmp_path, mocker):
        """Test process_single_file when extraction raises exception."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = b"fake image"

        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        extractor.extract.side_effect = Exception("LLM error")

        renamer = mocker.MagicMock(spec=FileRenamer)
        counter = {"done": 0}

        result = process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=True,
            verbose=False,
            confirm=False,
            counter=counter,
            total=1,
        )

        assert "extraction failed" in result.error
        assert counter["done"] == 1

    def test_skips_non_medical_receipt(self, tmp_path, mocker):
        """Test process_single_file skips non-medical receipts."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = b"fake image"

        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        extractor.extract.return_value = ReceiptData(is_medical_receipt=False)

        renamer = mocker.MagicMock(spec=FileRenamer)
        counter = {"done": 0}

        result = process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=True,
            verbose=False,
            confirm=False,
            counter=counter,
            total=1,
        )

        assert result.skipped_reason == "not a medical receipt"
        assert result.data.is_medical_receipt is False

    def test_generates_new_name_for_medical_receipt(self, tmp_path, mocker):
        """Test process_single_file generates new name for valid receipt."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = b"fake image"

        receipt_data = ReceiptData(
            is_medical_receipt=True,
            provider="CVS",
            patient="John",
            date="2024-01-15",
            amount=45.99,
        )
        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        extractor.extract.return_value = receipt_data

        renamer = mocker.MagicMock(spec=FileRenamer)
        renamer.generate_new_name.return_value = "2024-01-15_CVS_John_45.99.pdf"
        renamer.resolve_conflict.return_value = "2024-01-15_CVS_John_45.99.pdf"

        counter = {"done": 0}

        result = process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=True,
            verbose=False,
            confirm=False,
            counter=counter,
            total=1,
        )

        assert result.new_name == "2024-01-15_CVS_John_45.99.pdf"
        assert result.data == receipt_data
        # Dry run should not call execute_rename
        renamer.execute_rename.assert_not_called()

    def test_executes_rename_when_not_dry_run(self, tmp_path, mocker):
        """Test process_single_file executes rename when not dry run."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = b"fake image"

        receipt_data = ReceiptData(
            is_medical_receipt=True,
            provider="CVS",
            date="2024-01-15",
        )
        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        extractor.extract.return_value = receipt_data

        renamer = mocker.MagicMock(spec=FileRenamer)
        renamer.generate_new_name.return_value = "new_name.pdf"
        renamer.resolve_conflict.return_value = "new_name.pdf"

        counter = {"done": 0}

        process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=False,
            verbose=False,
            confirm=False,
            counter=counter,
            total=1,
        )

        renamer.execute_rename.assert_called_once_with(test_file, "new_name.pdf")

    def test_verbose_output(self, tmp_path, mocker, capsys):
        """Test process_single_file shows verbose output."""
        from receipt_organizer.extractor import ReceiptExtractor
        from receipt_organizer.processor import FileProcessor
        from receipt_organizer.renamer import FileRenamer

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        processor = mocker.MagicMock(spec=FileProcessor)
        processor.file_to_image_bytes.return_value = b"fake image"

        receipt_data = ReceiptData(
            is_medical_receipt=True,
            provider="CVS Pharmacy",
            patient="John Doe",
            date="2024-01-15",
            amount=45.99,
        )
        extractor = mocker.MagicMock(spec=ReceiptExtractor)
        extractor.extract.return_value = receipt_data

        renamer = mocker.MagicMock(spec=FileRenamer)
        renamer.generate_new_name.return_value = "new.pdf"
        renamer.resolve_conflict.return_value = "new.pdf"

        counter = {"done": 0}

        process_single_file(
            file_path=test_file,
            processor=processor,
            extractor=extractor,
            renamer=renamer,
            dry_run=True,
            verbose=True,
            confirm=False,
            counter=counter,
            total=1,
        )

        captured = capsys.readouterr()
        assert "Date: 2024-01-15" in captured.out
        assert "Provider: CVS Pharmacy" in captured.out
        assert "Patient: John Doe" in captured.out
