import httpx

from .config import Settings


class ElevenTTSClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def synthesize(self, text: str) -> bytes:
        if not self.settings.eleven_api_key or not self.settings.eleven_voice_id:
            raise RuntimeError("ELEVEN_API_KEY and ELEVEN_VOICE_ID are required for TTS")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.settings.eleven_voice_id}"
        headers = {
            "xi-api-key": self.settings.eleven_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.35, "similarity_boost": 0.8},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
