import os
from dotenv import load_dotenv

# Load environmental variables
load_dotenv()

class Config:
    PORT = int(os.getenv("PORT", "3000"))
    
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_REFINEMENT_MODEL = os.getenv("OLLAMA_REFINEMENT_MODEL", "llama3")
    OLLAMA_IMAGE_MODEL = os.getenv("OLLAMA_IMAGE_MODEL", "stable-diffusion")
    USE_OLLAMA_PROMPT_REFINEMENT = os.getenv("USE_OLLAMA_PROMPT_REFINEMENT", "false").lower() == "true"
    
    IMAGE_GENERATOR_PROVIDER = os.getenv("IMAGE_GENERATOR_PROVIDER", "pollinations")  # 'ollama', 'pollinations', 'local-mock'
    
    # Static files directory path
    PUBLIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))

config = Config()
