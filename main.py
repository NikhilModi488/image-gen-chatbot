import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import config
from app.routes.image_routes import router as api_router

app = FastAPI(
    title="AetherImage Text-to-Image Chatbot API",
    description="Backend API for Text-to-Image generation using local Ollama and fallbacks.",
    version="1.0.0"
)

# CORS Middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints first
app.include_router(api_router)

# Verify static directory exists and mount it at the root.
# This must be mounted after API routes to avoid overshadowing.
if os.path.exists(config.PUBLIC_PATH):
    app.mount("/", StaticFiles(directory=config.PUBLIC_PATH, html=True), name="public")
else:
    print(f"Warning: Static files directory '{config.PUBLIC_PATH}' does not exist.")

if __name__ == "__main__":
    print("==================================================")
    print(" Text-to-Image Chatbot Server (Python) starting...")
    print(f" Port: {config.PORT}")
    print(f" Local URL: http://localhost:{config.PORT}")
    print(f" Primary Image Provider: {config.IMAGE_GENERATOR_PROVIDER}")
    print("==================================================")
    
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
