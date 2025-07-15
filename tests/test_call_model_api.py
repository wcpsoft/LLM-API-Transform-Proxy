import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from src.main import call_model_api

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_call_model_api_basic(mock_post):
    mock_post.return_value.json = AsyncMock(return_value={"result": "ok"})
    mock_post.return_value.raise_for_status = AsyncMock(return_value=None)
    result = await call_model_api("openai", "test-model", {"messages": []}, stream=False)
    if asyncio.iscoroutine(result):
        result = await result
    assert result["result"] == "ok" 