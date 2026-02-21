import httpx

from .config import Settings


class ElevenSTTClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, audio_bytes: bytes, filename: str, content_type: str | None) -> str:
        if not self.settings.eleven_api_key:
            raise RuntimeError("ELEVEN_API_KEY is required for STT")

        files = {
            "file": (filename or "audio.webm", audio_bytes, content_type or "audio/webm"),
        }
        data = {"model_id": self.settings.eleven_stt_model_id}
        headers = {"xi-api-key": self.settings.eleven_api_key}

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers=headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            body = response.json()

        transcript = body.get("text") or body.get("transcript") or ""
        if not transcript:
            raise RuntimeError(f"Unexpected STT response payload: {body}")
        return transcript
