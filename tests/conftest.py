"""Shared pytest fixtures."""

from unittest.mock import MagicMock

import pytest

from receipt_organizer.models import ReceiptData


@pytest.fixture
def mock_ollama_client(mocker):
    """Mock Ollama client that returns predictable responses."""
    mock_response = MagicMock()
    mock_response.message.content = (
        '{"is_medical_receipt": true, "provider": "CVS Pharmacy", '
        '"patient": "John Doe", "date": "2024-01-15", "amount": 45.99}'
    )

    mock_client = MagicMock()
    mock_client.chat.return_value = mock_response

    mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)
    return mock_client


@pytest.fixture
def sample_receipt_data():
    """Sample ReceiptData for testing."""
    return ReceiptData(
        is_medical_receipt=True,
        provider="CVS Pharmacy",
        patient="John Doe",
        date="2024-01-15",
        amount=45.99,
    )
