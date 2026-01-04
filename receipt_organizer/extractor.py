"""Ollama vision model integration for receipt extraction."""

import base64

from ollama import Client

from .models import ReceiptData

EXTRACTION_PROMPT = """\
Analyze this medical receipt image and extract the following information.
Return ONLY a valid JSON object with these fields:

{
  "date": "YYYY-MM-DD format, or null if not visible",
  "provider": "Doctor, clinic, hospital, or pharmacy name",
  "patient": "Patient's full name",
  "amount": "Total amount as a number (no currency symbol)",
  "currency": "3-letter ISO currency code (see instructions below)",
  "is_medical_receipt": true or false
}

CURRENCY DETECTION - Look carefully at the receipt for:
- S$ or SGD = "SGD", $ with Singapore address = "SGD"
- RM = "MYR", € = "EUR", £ = "GBP", ¥ = "JPY"
- If the receipt shows a Singapore clinic/hospital/address, use SGD
- Only use "USD" if explicitly shown or if from a US provider
- If unclear, infer from the country/region shown on the receipt

If a field is not visible or unclear, use null for that field.
If this is NOT a medical receipt, set is_medical_receipt to false.

Return ONLY the JSON object, no other text."""


class ReceiptExtractor:
    """Extracts receipt data using local Ollama vision model."""

    def __init__(self, model: str = "qwen2.5vl:7b", timeout: float = 120.0):
        """Initialize extractor with Ollama client.

        Args:
            model: Ollama model name (must support vision)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.client = Client(host="http://localhost:11434", timeout=timeout)

    def check_available(self) -> tuple[bool, str]:
        """Check if Ollama is running and model is available.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # List models to check connection
            models = self.client.list()
            model_names = [m.model for m in models.models]

            # Check if our model is available
            if not any(self.model in name for name in model_names):
                return (
                    False,
                    f"Model '{self.model}' not found. Run: ollama pull {self.model}",
                )

            return True, ""
        except Exception as e:
            return (
                False,
                f"Cannot connect to Ollama: {e}\n"
                "Make sure Ollama is running: ollama serve",
            )

    def extract(self, image_bytes: bytes) -> ReceiptData:
        """Extract receipt data from image bytes.

        Args:
            image_bytes: Image data as bytes (PNG or JPG)

        Returns:
            ReceiptData with extracted fields
        """
        # Encode image as base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "user", "content": EXTRACTION_PROMPT, "images": [image_b64]}
            ],
            options={"temperature": 0},  # Deterministic output
        )

        return ReceiptData.from_json(response.message.content)
