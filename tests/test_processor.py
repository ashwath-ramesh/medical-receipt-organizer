"""Tests for processor module."""

from receipt_organizer.processor import FileProcessor


class TestFileProcessor:
    def test_discover_files_finds_supported_types(self, tmp_path):
        # Create various file types
        (tmp_path / "receipt.pdf").touch()
        (tmp_path / "image.jpg").touch()
        (tmp_path / "image.png").touch()
        (tmp_path / "ignore.txt").touch()
        (tmp_path / "ignore.doc").touch()

        processor = FileProcessor()
        files = processor.discover_files(tmp_path)

        filenames = [f.name for f in files]
        assert "receipt.pdf" in filenames
        assert "image.jpg" in filenames
        assert "image.png" in filenames
        assert "ignore.txt" not in filenames
        assert "ignore.doc" not in filenames

    def test_discover_files_recursive(self, tmp_path):
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "top.pdf").touch()
        (subdir / "nested.pdf").touch()

        processor = FileProcessor()
        files = processor.discover_files(tmp_path)

        filenames = [f.name for f in files]
        assert "top.pdf" in filenames
        assert "nested.pdf" in filenames

    def test_discover_files_case_insensitive(self, tmp_path):
        (tmp_path / "UPPER.PDF").touch()
        (tmp_path / "lower.pdf").touch()
        (tmp_path / "Mixed.Pdf").touch()

        processor = FileProcessor()
        files = processor.discover_files(tmp_path)

        # Should find at least uppercase and lowercase
        assert len(files) >= 2

    def test_discover_files_empty_directory(self, tmp_path):
        processor = FileProcessor()
        files = processor.discover_files(tmp_path)
        assert files == []

    def test_discover_files_no_duplicates(self, tmp_path):
        (tmp_path / "test.pdf").touch()

        processor = FileProcessor()
        files = processor.discover_files(tmp_path)

        # Should not have duplicates
        assert len(files) == len(set(files))

    def test_supported_extensions(self):
        processor = FileProcessor()
        expected = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
        assert processor.SUPPORTED_EXTENSIONS == expected

    def test_default_dpi(self):
        processor = FileProcessor()
        assert processor.dpi == 400

    def test_custom_dpi(self):
        processor = FileProcessor(dpi=300)
        assert processor.dpi == 300

    def test_file_to_image_bytes_invalid_file(self, tmp_path):
        # Create an invalid PDF
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"not a real pdf")

        processor = FileProcessor()
        result = processor.file_to_image_bytes(bad_pdf)

        # Should return None for invalid files
        assert result is None

    def test_file_to_image_bytes_nonexistent(self, tmp_path):
        processor = FileProcessor()
        result = processor.file_to_image_bytes(tmp_path / "nonexistent.pdf")
        assert result is None
