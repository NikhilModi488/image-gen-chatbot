import time
import logging
from app.services.ollama_service import OllamaService
from app.services.generator_service import GeneratorService
from app.config import config

logger = logging.getLogger(__name__)

def check_is_greeting_fallback(prompt: str) -> str:
    """
    Checks if the user prompt is a greeting or a simple conversational message.
    If yes, returns the conversational response. If not, returns None.
    """
    clean_prompt = prompt.strip().lower().rstrip("?.!")
    greetings = {
        "hi", "hello", "hey", "howdy", "greetings", "yo", "sup", "hello there", "hi there", "hey there",
        "good morning", "good afternoon", "good evening", "goodnight", "namaste"
    }
    
    # Direct match or startswith matching
    if clean_prompt in greetings or any(clean_prompt.startswith(g + " ") for g in greetings):
        return "Hello! I am AetherImage Chatbot. How can I help you visualize your ideas today? Describe any scene you want to generate!"
    return None

class ImageService:
    @staticmethod
    async def generate_image(prompt: str, refine: bool = False, history: list = None, model: str = None, gemini_api_key: str = None, seed: int = None) -> dict:
        """
        Orchestrates prompt refinement and image generation, tracking timing.
        """
        import random
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required")

        # 1. Check fallback greeting list first for instant zero-latency match
        fallback_text = check_is_greeting_fallback(prompt)
        if fallback_text:
            return {
                "isGreeting": True,
                "message": fallback_text,
                "originalPrompt": prompt,
                "refinedPrompt": None,
                "image": None,
                "source": "Conversational Assistant",
                "duration": 0,
                "seed": None
            }

        # 2. Query the LLM Routing Layer (Chit-chat & Clarifications)
        try:
            route = await OllamaService.classify_and_route_input(prompt, history)
            if route["action"] in ["chitchat", "clarify"]:
                return {
                    "isGreeting": True,
                    "message": route["message"],
                    "originalPrompt": prompt,
                    "refinedPrompt": None,
                    "image": None,
                    "source": "Conversational Assistant",
                    "duration": 0,
                    "seed": None
                }
        except Exception as e:
            logger.error(f"Routing layer failed, proceeding to generation. Error: {e}")

        start_time = time.time()
        final_prompt = prompt.strip()
        refined_prompt = None
        active_seed = seed if seed is not None else random.randint(1, 1000000)

        # 1. LLM Prompt Refinement Layer (Always use local Ollama)
        should_refine = refine or config.USE_OLLAMA_PROMPT_REFINEMENT
        if should_refine:
            try:
                logger.info("Initiating prompt refinement layer...")
                refined_prompt = await OllamaService.refine_prompt(final_prompt, history)
                
                if refined_prompt:
                    final_prompt = refined_prompt
            except Exception as e:
                logger.error(f"Prompt refinement layer failed, using raw prompt. Error: {e}")

        # 2. Generate the image
        logger.info(f"Generating image for: '{final_prompt}' (model: {model}, seed: {active_seed})")
        generator_result = await GeneratorService.generate_image(final_prompt, model, gemini_api_key, active_seed)

        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Generation completed in {duration_ms}ms via {generator_result['source']}")

        return {
            "originalPrompt": prompt,
            "refinedPrompt": refined_prompt,
            "image": generator_result["image"],
            "source": generator_result["source"],
            "duration": duration_ms,
            "seed": active_seed
        }
