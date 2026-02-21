## Voice Agent Module

Drop-in FastAPI router available at `src/voice_agent/api.py` exposing:
- `POST /api/agent/turn` for transcript -> intent + UI action.
- `POST /api/agent/stt` for audio blob -> transcript (ElevenLabs STT).
- `POST /api/agent/tts` for text -> audio/mpeg stream.
- `GET /api/agent/demo` for a continuous-microphone demo webpage.

Wire it into an app with:

```python
from src.voice_agent.api import router as voice_agent_router
app.include_router(voice_agent_router, prefix="")
```

Install deps, set env vars, and run:

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
export GEMINI_MODEL=gemini-2.0-flash  # optional, defaults to this and auto-falls back to gemini-1.5-flash
export ELEVEN_API_KEY=...
export ELEVEN_VOICE_ID=...
uvicorn src.main:app --reload
```

If you changed env vars, restart uvicorn.
Then open `http://localhost:8000/api/agent/demo` and click **Start Mic**.


Quick run (fast path):

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
export ELEVEN_API_KEY=...
export ELEVEN_VOICE_ID=...
uvicorn src.main:app --reload --port 8000
```
