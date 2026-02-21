import json
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from .config import Settings
from .schema import Intent


class GeminiIntentClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._intent_adapter = TypeAdapter(Intent)

    async def parse_intent(self, transcript: str, payees_allowed: list[str]) -> Intent:
        if not self.settings.gemini_api_key:
            return self._intent_adapter.validate_python(
                {
                    "intent": "CLARIFY",
                    "assistant_say": "I did not understand that. Please try again.",
                    "choices": ["Check my balance", "Send 20 euros to James (Son)"],
                }
            )

        prompt = self._prompt(transcript, payees_allowed)
        raw = await self._call_gemini(prompt)
        return await self._validate_with_repair(raw, transcript, payees_allowed)

    def _prompt(self, transcript: str, payees_allowed: list[str]) -> str:
        return (
            "You are a banking intent parser. Return JSON only. "
            "Allowed intents: CHECK_BALANCE, TRANSFER_DRAFT, CONFIRM, CANCEL, CLARIFY, HELP. "
            f"Allowed payees: {payees_allowed}. Currency must be EUR. "
            f"User transcript: {transcript}"
        )

    async def _call_gemini(self, prompt: str) -> dict[str, Any]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "intent": {
                            "type": "STRING",
                            "enum": [
                                "CHECK_BALANCE",
                                "TRANSFER_DRAFT",
                                "CONFIRM",
                                "CANCEL",
                                "CLARIFY",
                                "HELP",
                            ],
                        },
                        "payee_label": {"type": "STRING"},
                        "amount": {"type": "NUMBER"},
                        "currency": {"type": "STRING"},
                        "assistant_say": {"type": "STRING"},
                        "choices": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["intent", "assistant_say"],
                },
            },
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    async def _validate_with_repair(self, raw: dict[str, Any], transcript: str, payees_allowed: list[str]) -> Intent:
        try:
            return self._intent_adapter.validate_python(raw)
        except ValidationError:
            repair_prompt = (
                "Repair this intent JSON to match the schema. JSON only. "
                f"Allowed payees: {payees_allowed}. Transcript: {transcript}. Raw: {raw}"
            )
            try:
                repaired = await self._call_gemini(repair_prompt)
                return self._intent_adapter.validate_python(repaired)
            except Exception:
                return self._intent_adapter.validate_python(
                    {
                        "intent": "CLARIFY",
                        "assistant_say": "I need clarification before proceeding.",
                        "choices": payees_allowed,
                    }
                )
