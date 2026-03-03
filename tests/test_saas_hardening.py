import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from apps.api.phase4_routes import (
    _validate_ai_provider,
    _validate_custom_endpoint,
    _serialize_settings_for_audit,
)
from packages.shared.models import Position
from packages.shared.llm_adapter import GeminiAdapter


def test_validate_ai_provider_allows_supported_values():
    assert _validate_ai_provider("openai") == "openai"
    assert _validate_ai_provider("GEMINI") == "gemini"
    assert _validate_ai_provider(" claude ") == "claude"


def test_validate_ai_provider_rejects_unknown():
    with pytest.raises(HTTPException) as exc:
        _validate_ai_provider("unknown-provider")
    assert exc.value.status_code == 400


def test_validate_custom_endpoint_rejects_localhost_and_private_ip():
    with pytest.raises(HTTPException):
        _validate_custom_endpoint("http://localhost:8000/v1")

    with pytest.raises(HTTPException):
        _validate_custom_endpoint("http://127.0.0.1:1234/v1")

    with pytest.raises(HTTPException):
        _validate_custom_endpoint("http://10.0.0.10:8080/v1")


def test_validate_custom_endpoint_accepts_public_https_url():
    assert (
        _validate_custom_endpoint("https://api.openai.com/v1")
        == "https://api.openai.com/v1"
    )


def test_serialize_settings_for_audit_masks_secrets():
    data = _serialize_settings_for_audit()
    for key in (
        "binance_api_key",
        "binance_api_secret",
        "telegram_bot_token",
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "groq_api_key",
    ):
        val = data.get(key, "")
        assert ("***" in val) or (val == "") or (val == "****")


def test_position_has_tenant_scoped_unique_constraint():
    uq_names = {c.name for c in Position.__table__.constraints}
    assert "uq_positions_user_symbol" in uq_names


@pytest.mark.asyncio
async def test_gemini_adapter_raises_on_429_no_mock_fallback():
    adapter = GeminiAdapter(api_key="test-key", model="gemini-2.0-flash")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "quota exceeded"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError) as exc:
            await adapter.generate("test prompt")
        assert "429" in str(exc.value)
