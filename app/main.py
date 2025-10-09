from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, chat, file_upload, analysis, location

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(file_upload.router, prefix="/files", tags=["files"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(location.router, prefix="/location", tags=["location"])

@app.get("/")
def root():
    return {"message": "DataGround AI Assistant with Google ADK Multi-Agent System running"}
