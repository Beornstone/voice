from pydantic import TypeAdapter

from .config import get_settings
from .gemini_client import GeminiIntentClient
from .schema import ClarifyIntent, Intent, TurnResponse
from .session_store import SessionState, session_store

INTENT_ADAPTER = TypeAdapter(Intent)


async def handle_turn(session_id: str, transcript: str) -> TurnResponse:
    state = session_store.get(session_id)
    client = GeminiIntentClient(get_settings())
    intent = await client.parse_intent(transcript, state.payees_allowed)
    intent, ui_action = _apply_state_machine(state, intent)

    debug = None
    if get_settings().debug_responses:
        debug = {
            "transcript": transcript,
            "session_id": session_id,
            "pending_transfer": state.pending_transfer,
        }

    return TurnResponse(
        assistant_say=intent.assistant_say,
        intent=intent,
        ui_action=ui_action,
        debug=debug,
    )


def _clarify(message: str, choices: list[str] | None = None) -> Intent:
    return INTENT_ADAPTER.validate_python(
        ClarifyIntent(intent="CLARIFY", assistant_say=message, choices=choices).model_dump()
    )


def _apply_state_machine(state: SessionState, intent: Intent) -> tuple[Intent, dict | None]:
    if intent.intent == "CHECK_BALANCE":
        state.screen = "balance"
        intent.assistant_say = "Your balance is 1234.56 EUR."
        return intent, {"type": "OPEN_BALANCE"}

    if intent.intent == "TRANSFER_DRAFT":
        if intent.payee_label not in state.payees_allowed:
            return _clarify(
                "I can only pay approved contacts. Which payee should I use?",
                state.payees_allowed,
            ), None
        if intent.amount <= 0 or intent.amount > 10000:
            return _clarify("Amount must be greater than 0 and up to 10000 EUR."), None

        state.pending_transfer = {
            "payee_label": intent.payee_label,
            "amount": intent.amount,
            "currency": intent.currency,
        }
        state.screen = "transfer"
        return intent, {
            "type": "OPEN_TRANSFER",
            "payee_label": intent.payee_label,
            "amount": intent.amount,
            "currency": intent.currency,
        }

    if intent.intent == "CONFIRM":
        if not state.pending_transfer:
            return _clarify(
                "There is no transfer waiting for confirmation.",
                ["Send money", "Check balance"],
            ), None
        state.pending_transfer = None
        intent.assistant_say = "Confirmed. Ready to send."
        return intent, {"type": "HIGHLIGHT_SEND"}

    if intent.intent == "CANCEL":
        state.pending_transfer = None
        state.screen = "home"
        intent.assistant_say = "Cancelled. Returning home."
        return intent, {"type": "GO_HOME"}

    if intent.intent in {"CLARIFY", "HELP"}:
        return intent, None

    return intent, None
