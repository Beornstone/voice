import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from src.voice_agent import router as agent_router
from src.voice_agent.session_store import session_store


@pytest.mark.asyncio
async def test_transfer_draft_sets_pending_and_open_transfer(monkeypatch):
    async def fake_parse_intent(self, transcript, payees_allowed):
        return agent_router.INTENT_ADAPTER.validate_python(
            {
                "intent": "TRANSFER_DRAFT",
                "payee_label": "James (Son)",
                "amount": 20,
                "currency": "EUR",
                "assistant_say": "Drafting transfer now.",
            }
        )

    monkeypatch.setattr(agent_router.GeminiIntentClient, "parse_intent", fake_parse_intent)

    response = await agent_router.handle_turn("s-transfer", "send 20")
    assert response.intent.intent == "TRANSFER_DRAFT"
    assert response.ui_action and response.ui_action.type == "OPEN_TRANSFER"
    assert session_store.get("s-transfer").pending_transfer == {
        "payee_label": "James (Son)",
        "amount": 20.0,
        "currency": "EUR",
    }


@pytest.mark.asyncio
async def test_confirm_without_pending_returns_clarify(monkeypatch):
    async def fake_parse_intent(self, transcript, payees_allowed):
        return agent_router.INTENT_ADAPTER.validate_python(
            {
                "intent": "CONFIRM",
                "assistant_say": "confirm",
            }
        )

    monkeypatch.setattr(agent_router.GeminiIntentClient, "parse_intent", fake_parse_intent)

    response = await agent_router.handle_turn("s-confirm-none", "confirm")
    assert response.intent.intent == "CLARIFY"
    assert response.ui_action is None


@pytest.mark.asyncio
async def test_cancel_clears_pending_and_go_home(monkeypatch):
    state = session_store.get("s-cancel")
    state.pending_transfer = {"payee_label": "James (Son)", "amount": 10, "currency": "EUR"}

    async def fake_parse_intent(self, transcript, payees_allowed):
        return agent_router.INTENT_ADAPTER.validate_python(
            {
                "intent": "CANCEL",
                "assistant_say": "cancel",
            }
        )

    monkeypatch.setattr(agent_router.GeminiIntentClient, "parse_intent", fake_parse_intent)

    response = await agent_router.handle_turn("s-cancel", "cancel")
    assert response.intent.intent == "CANCEL"
    assert response.ui_action and response.ui_action.type == "GO_HOME"
    assert session_store.get("s-cancel").pending_transfer is None
