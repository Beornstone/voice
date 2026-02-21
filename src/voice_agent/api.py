from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from .config import get_settings
from .eleven_stt import ElevenSTTClient
from .eleven_tts import ElevenTTSClient
from .router import handle_turn
from .schema import TTSRequest, TurnRequest, TurnResponse

router = APIRouter()


@router.post("/api/agent/turn", response_model=TurnResponse)
async def agent_turn(payload: TurnRequest) -> TurnResponse:
    return await handle_turn(payload.session_id, payload.transcript)


@router.post("/api/agent/tts")
async def agent_tts(payload: TTSRequest) -> StreamingResponse:
    client = ElevenTTSClient(get_settings())
    try:
        audio = await client.synthesize(payload.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {exc}") from exc
    return StreamingResponse(iter([audio]), media_type="audio/mpeg")


@router.post("/api/agent/stt")
async def agent_stt(audio: UploadFile = File(...)) -> dict:
    client = ElevenSTTClient(get_settings())
    try:
        transcript = await client.transcribe(await audio.read(), audio.filename or "audio.webm", audio.content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"STT failed: {exc}") from exc
    return {"transcript": transcript}


@router.get("/api/agent/demo", response_class=HTMLResponse)
async def agent_demo() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html>
  <head><meta charset='utf-8'><title>Voice Agent Demo</title></head>
  <body style='font-family: sans-serif; max-width: 760px; margin: 20px auto;'>
    <h2>Voice Agent Demo</h2>
    <p>1) Set GEMINI_API_KEY, ELEVEN_API_KEY, ELEVEN_VOICE_ID. 2) Click Start. 3) Speak continuously.</p>
    <button id='start'>Start Mic</button>
    <button id='stop' disabled>Stop Mic</button>
    <pre id='log' style='white-space: pre-wrap; background:#f5f5f5; padding:12px; min-height:300px;'></pre>
    <script>
      const sessionId = 'web-' + Math.random().toString(36).slice(2);
      const logEl = document.getElementById('log');
      const append = (x) => logEl.textContent = `[${new Date().toLocaleTimeString()}] ${x}\n` + logEl.textContent;
      let recorder;
      let stream;
      let running = false;

      async function handleChunk(blob) {
        if (!blob || blob.size === 0 || !running) return;
        const fd = new FormData();
        fd.append('audio', blob, 'chunk.webm');

        const sttRes = await fetch('/api/agent/stt', { method: 'POST', body: fd });
        if (!sttRes.ok) { append('STT error: ' + await sttRes.text()); return; }
        const stt = await sttRes.json();
        const transcript = (stt.transcript || '').trim();
        if (!transcript) return;
        append('User: ' + transcript);

        const turnRes = await fetch('/api/agent/turn', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ session_id: sessionId, transcript })
        });
        if (!turnRes.ok) { append('TURN error: ' + await turnRes.text()); return; }
        const turn = await turnRes.json();
        append('Intent: ' + JSON.stringify(turn.intent));
        append('UI Action: ' + JSON.stringify(turn.ui_action));
        append('Assistant: ' + turn.assistant_say);

        const ttsRes = await fetch('/api/agent/tts', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ text: turn.assistant_say })
        });
        if (!ttsRes.ok) { append('TTS error: ' + await ttsRes.text()); return; }
        const audioBlob = await ttsRes.blob();
        const url = URL.createObjectURL(audioBlob);
        const audio = new Audio(url);
        await audio.play();
        audio.onended = () => URL.revokeObjectURL(url);
      }

      document.getElementById('start').onclick = async () => {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        running = true;
        recorder.ondataavailable = (e) => { handleChunk(e.data).catch(err => append('Error: ' + err.message)); };
        recorder.start(2500);
        append('Mic started, continuous chunk streaming enabled.');
        document.getElementById('start').disabled = true;
        document.getElementById('stop').disabled = false;
      };

      document.getElementById('stop').onclick = () => {
        running = false;
        if (recorder && recorder.state !== 'inactive') recorder.stop();
        if (stream) stream.getTracks().forEach(t => t.stop());
        append('Mic stopped.');
        document.getElementById('start').disabled = false;
        document.getElementById('stop').disabled = true;
      };
    </script>
  </body>
</html>
        """.strip()
    )
