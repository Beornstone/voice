from fastapi import FastAPI

from src.voice_agent.api import router as voice_agent_router

app = FastAPI()
app.include_router(voice_agent_router, prefix="")
