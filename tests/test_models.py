"""Tests for models module."""

from receipt_organizer.models import ReceiptData


class TestReceiptData:
    def test_from_json_valid(self):
        json_str = '{"date": "2024-01-15", "provider": "CVS", "amount": 45.99}'
        result = ReceiptData.from_json(json_str)
        assert result.date == "2024-01-15"
        assert result.provider == "CVS"
        assert result.amount == 45.99

    def test_from_json_with_extra_text(self):
        # LLM sometimes returns JSON wrapped in text
        json_str = 'Here is the data: {"date": "2024-01-15", "provider": "CVS"} done'
        result = ReceiptData.from_json(json_str)
        assert result.date == "2024-01-15"
        assert result.provider == "CVS"

    def test_from_json_amount_as_string(self):
        json_str = '{"amount": "$45.99"}'
        result = ReceiptData.from_json(json_str)
        assert result.amount == 45.99

    def test_from_json_amount_with_currency_symbol(self):
        json_str = '{"amount": "USD 100.50"}'
        result = ReceiptData.from_json(json_str)
        assert result.amount == 100.50

    def test_from_json_invalid_amount_string(self):
        json_str = '{"amount": "not a number"}'
        result = ReceiptData.from_json(json_str)
        assert result.amount is None

    def test_from_json_invalid_json(self):
        json_str = "not json at all"
        result = ReceiptData.from_json(json_str)
        assert result.is_medical_receipt is False

    def test_from_json_ignores_unknown_fields(self):
        json_str = '{"date": "2024-01-15", "unknown_field": "ignored"}'
        result = ReceiptData.from_json(json_str)
        assert result.date == "2024-01-15"
        assert not hasattr(result, "unknown_field")

    def test_from_json_all_fields(self):
        json_str = """
        {
            "date": "2024-01-15",
            "provider": "CVS Pharmacy",
            "patient": "John Doe",
            "amount": 45.99,
            "currency": "SGD",
            "is_medical_receipt": true
        }
        """
        result = ReceiptData.from_json(json_str)
        assert result.date == "2024-01-15"
        assert result.provider == "CVS Pharmacy"
        assert result.patient == "John Doe"
        assert result.amount == 45.99
        assert result.currency == "SGD"
        assert result.is_medical_receipt is True

    def test_default_values(self):
        data = ReceiptData()
        assert data.date is None
        assert data.provider is None
        assert data.patient is None
        assert data.amount is None
        assert data.currency == "USD"
        assert data.is_medical_receipt is True
