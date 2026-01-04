"""Tests for extractor module."""

from unittest.mock import MagicMock

from receipt_organizer.extractor import ReceiptExtractor


class TestReceiptExtractor:
    def test_extract_returns_receipt_data(self, mock_ollama_client):
        extractor = ReceiptExtractor()
        result = extractor.extract(b"fake image bytes")
        assert result.is_medical_receipt is True
        assert result.provider == "CVS Pharmacy"
        assert result.amount == 45.99

    def test_extract_non_receipt(self, mocker):
        mock_response = MagicMock()
        mock_response.message.content = '{"is_medical_receipt": false}'
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)

        extractor = ReceiptExtractor()
        result = extractor.extract(b"random image")
        assert result.is_medical_receipt is False

    def test_check_available_success(self, mocker):
        mock_model = MagicMock()
        mock_model.model = "qwen2.5vl:7b"
        mock_list_response = MagicMock()
        mock_list_response.models = [mock_model]

        mock_client = MagicMock()
        mock_client.list.return_value = mock_list_response
        mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)

        extractor = ReceiptExtractor(model="qwen2.5vl:7b")
        available, error = extractor.check_available()
        assert available is True
        assert error == ""

    def test_check_available_model_not_found(self, mocker):
        mock_model = MagicMock()
        mock_model.model = "other-model"
        mock_list_response = MagicMock()
        mock_list_response.models = [mock_model]

        mock_client = MagicMock()
        mock_client.list.return_value = mock_list_response
        mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)

        extractor = ReceiptExtractor(model="qwen2.5vl:7b")
        available, error = extractor.check_available()
        assert available is False
        assert "not found" in error

    def test_check_available_connection_error(self, mocker):
        mock_client = MagicMock()
        mock_client.list.side_effect = Exception("Connection refused")
        mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)

        extractor = ReceiptExtractor()
        available, error = extractor.check_available()
        assert available is False
        assert "Cannot connect" in error

    def test_extract_sends_correct_prompt(self, mocker):
        mock_response = MagicMock()
        mock_response.message.content = '{"is_medical_receipt": true}'
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        mocker.patch("receipt_organizer.extractor.Client", return_value=mock_client)

        extractor = ReceiptExtractor(model="test-model")
        extractor.extract(b"test image")

        # Verify chat was called with correct model
        mock_client.chat.assert_called_once()
        call_kwargs = mock_client.chat.call_args
        assert call_kwargs.kwargs["model"] == "test-model"
        assert len(call_kwargs.kwargs["messages"]) == 1
        assert "images" in call_kwargs.kwargs["messages"][0]
