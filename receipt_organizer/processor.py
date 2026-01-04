"""File discovery and image conversion."""

from pathlib import Path

import pymupdf  # PyMuPDF


class FileProcessor:
    """Discovers and converts receipt files to images for processing."""

    SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

    def __init__(self, dpi: int = 400):
        """Initialize processor.

        Args:
            dpi: Resolution for PDF rendering (400 for better OCR quality)
        """
        self.dpi = dpi

    def discover_files(self, directory: Path) -> list[Path]:
        """Recursively find all supported files in directory.

        Args:
            directory: Root directory to scan

        Returns:
            List of file paths sorted by name
        """
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(directory.rglob(f"*{ext}"))
            files.extend(directory.rglob(f"*{ext.upper()}"))

        # Remove duplicates and sort
        return sorted(set(files))

    def file_to_image_bytes(self, file_path: Path) -> bytes | None:
        """Convert file to PNG image bytes for vision model.

        For PDFs, renders the first page.
        For images, reads directly.

        Args:
            file_path: Path to the file

        Returns:
            PNG image bytes, or None if conversion fails
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".pdf":
                return self._pdf_to_png(file_path)
            else:
                return self._image_to_png(file_path)
        except Exception:
            return None

    def _pdf_to_png(self, pdf_path: Path) -> bytes:
        """Render first page of PDF to PNG bytes."""
        with pymupdf.open(str(pdf_path)) as doc:
            page = doc[0]  # First page only
            pix = page.get_pixmap(dpi=self.dpi)
            return pix.tobytes("png")

    def _image_to_png(self, image_path: Path) -> bytes:
        """Convert image file to PNG bytes, normalized to DPI limit."""
        with pymupdf.open(str(image_path)) as doc:
            page = doc[0]
            pix = page.get_pixmap(dpi=self.dpi)
            return pix.tobytes("png")
