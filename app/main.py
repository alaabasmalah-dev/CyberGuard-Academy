from dotenv import load_dotenv
load_dotenv()  # must run before importing modules that read os.getenv() at import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth, progress, quiz, mentor, oauth

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="CyberPulse API")

# Allow both frontends (Bolt project on a fixed port, Cyber-Pulse on a
# Replit-assigned dynamic port) to call this API from the browser during dev.
# When you deploy for real, replace the regex below with your actual
# frontend domain(s) in allow_origins for tighter security.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(progress.router)
app.include_router(quiz.router)
app.include_router(mentor.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
