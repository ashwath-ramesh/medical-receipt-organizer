"""Data models for receipt extraction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class ReceiptData:
    """Extracted receipt information from vision model."""

    date: str | None = None  # YYYY-MM-DD format
    provider: str | None = None  # Doctor, clinic, or pharmacy
    patient: str | None = None  # Patient name
    amount: float | None = None  # Total amount
    currency: str = "USD"  # Currency code
    is_medical_receipt: bool = True  # Whether this is a medical receipt

    @classmethod
    def from_json(cls, json_str: str) -> ReceiptData:
        """Parse LLM JSON response into ReceiptData.

        Handles malformed JSON by extracting JSON object from response.
        """
        # Try to extract JSON from response (LLM may include extra text)
        json_match = re.search(r"\{[^{}]*\}", json_str, re.DOTALL)
        if json_match:
            json_str = json_match.group()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Return empty data if JSON parsing fails
            return cls(is_medical_receipt=False)

        # Filter to only known fields
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}

        # Handle amount as string or number
        if "amount" in filtered and isinstance(filtered["amount"], str):
            try:
                filtered["amount"] = float(re.sub(r"[^\d.]", "", filtered["amount"]))
            except ValueError:
                filtered["amount"] = None

        return cls(**filtered)
