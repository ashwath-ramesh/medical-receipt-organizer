"""Filename generation and file renaming logic."""

import re
from pathlib import Path

from .models import ReceiptData


class FileRenamer:
    """Generates new filenames and handles rename operations."""

    PLACEHOLDER_UNKNOWN = "UNKNOWN"
    PLACEHOLDER_REVIEW = "REVIEW"
    MAX_FIELD_LENGTH = 30
    MAX_CONFLICT_ATTEMPTS = 1000

    def sanitize(self, text: str | None, max_length: int = MAX_FIELD_LENGTH) -> str:
        """Sanitize text for use in filenames.

        Removes special characters, replaces spaces with camelCase,
        and truncates to max length.
        """
        if not text:
            return self.PLACEHOLDER_UNKNOWN

        # Remove special characters except spaces and alphanumeric
        text = re.sub(r"[^\w\s]", "", text)

        # Convert to camelCase-like: "John Doe" -> "JohnDoe"
        words = text.split()
        text = "".join(word.capitalize() for word in words)

        # Truncate
        if len(text) > max_length:
            text = text[:max_length]

        return text if text else self.PLACEHOLDER_UNKNOWN

    def format_amount(self, amount: float | None, currency: str = "USD") -> str:
        """Format amount with currency for filename."""
        if amount is None:
            return self.PLACEHOLDER_UNKNOWN

        # Format as integer if whole number, else 2 decimals
        if amount == int(amount):
            return f"{currency}{int(amount)}"
        else:
            return f"{currency}{amount:.2f}"

    def generate_new_name(self, data: ReceiptData, original_ext: str) -> str:
        """Generate new filename from extracted data.

        Format: YYYY-MM-DD_Provider_Patient_Amount.ext

        Args:
            data: Extracted receipt data
            original_ext: Original file extension (e.g., '.pdf')

        Returns:
            New filename (not full path)
        """
        # Date - use REVIEW if missing (needs manual attention)
        if data.date and re.match(r"\d{4}-\d{2}-\d{2}", data.date):
            date_part = data.date
        else:
            date_part = self.PLACEHOLDER_REVIEW

        # Other fields
        provider = self.sanitize(data.provider)
        patient = self.sanitize(data.patient)
        amount = self.format_amount(data.amount, data.currency)

        # Combine
        name = f"{date_part}_{provider}_{patient}_{amount}{original_ext}"

        return name

    def resolve_conflict(self, directory: Path, filename: str) -> str:
        """Add suffix if filename already exists.

        Args:
            directory: Directory where file will be placed
            filename: Proposed filename

        Returns:
            Unique filename with _1, _2, etc. suffix if needed
        """
        target = directory / filename
        if not target.exists():
            return filename

        # Split name and extension
        stem = target.stem
        ext = target.suffix

        # Find unique suffix
        for counter in range(1, self.MAX_CONFLICT_ATTEMPTS + 1):
            new_name = f"{stem}_{counter}{ext}"
            if not (directory / new_name).exists():
                return new_name
        msg = f"Could not resolve conflict after {self.MAX_CONFLICT_ATTEMPTS} attempts"
        raise RuntimeError(msg)

    def execute_rename(self, source: Path, new_name: str) -> Path:
        """Rename file to new name in same directory.

        Args:
            source: Current file path
            new_name: New filename (not full path)

        Returns:
            New file path
        """
        new_path = source.parent / new_name

        # Validate path stays within source directory (prevent path traversal)
        if new_path.resolve().parent != source.parent.resolve():
            raise ValueError(f"Path traversal detected: {new_name}")

        source.rename(new_path)
        return new_path
