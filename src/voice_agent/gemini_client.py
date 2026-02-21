import json

from google import genai
from pydantic import TypeAdapter, ValidationError

from .config import Settings
from .schema import Intent


class GeminiIntentClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._intent_adapter = TypeAdapter(Intent)
        self._client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    async def parse_intent(self, transcript: str, payees_allowed: list[str]) -> Intent:
        if not self.settings.gemini_api_key or self._client is None:
            return self._intent_adapter.validate_python(
                {
                    "intent": "CLARIFY",
                    "assistant_say": "I did not understand that. Please try again.",
                    "choices": ["Check my balance", "Send 20 euros to James (Son)"],
                }
            )

        prompt = self._prompt(transcript, payees_allowed)
        raw = self._call_gemini(prompt)
        return self._validate_with_repair(raw, transcript, payees_allowed)

    def _prompt(self, transcript: str, payees_allowed: list[str]) -> str:
        return (
            "You are a banking intent parser. Return JSON only. "
            "Allowed intents: CHECK_BALANCE, TRANSFER_DRAFT, CONFIRM, CANCEL, CLARIFY, HELP. "
            f"Allowed payees: {payees_allowed}. Currency must be EUR. "
            "Return only a single valid JSON object with the intent fields. "
            f"User transcript: {transcript}"
        )

    def _call_gemini(self, prompt: str) -> dict:
        if self._client is None:
            raise RuntimeError("Gemini client not initialized")

        model_sequence = [self.settings.gemini_model]
        if self.settings.gemini_model == "gemini-2.0-flash":
            model_sequence.append("gemini-1.5-flash")

        last_error: Exception | None = None
        for model_name in model_sequence:
            try:
                response = self._client.models.generate_content(model=model_name, contents=prompt)
                text = response.text or ""
                return self._extract_json_object(text)
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                if model_name == "gemini-2.0-flash" and ("404" in message or "not found" in message or "invalid" in message):
                    continue
                break

        raise RuntimeError("Gemini request failed") from last_error

    def _extract_json_object(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("Gemini response did not include JSON")
        return json.loads(text[start : end + 1])

    def _validate_with_repair(self, raw: dict, transcript: str, payees_allowed: list[str]) -> Intent:
        try:
            return self._intent_adapter.validate_python(raw)
        except ValidationError:
            repair_prompt = (
                "Repair this intent JSON to match the schema. JSON only. "
                f"Allowed payees: {payees_allowed}. Transcript: {transcript}. Raw: {raw}"
            )
            try:
                repaired = self._call_gemini(repair_prompt)
                return self._intent_adapter.validate_python(repaired)
            except Exception:
                return self._intent_adapter.validate_python(
                    {
                        "intent": "CLARIFY",
                        "assistant_say": "I need clarification before proceeding.",
                        "choices": payees_allowed,
                    }
                )
