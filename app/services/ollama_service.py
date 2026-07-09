import httpx
import logging
from app.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REFINEMENT_SYSTEM_INSTRUCTION = (
    "You are an expert prompt engineer for text-to-image.\n"
    "The user is using a chatbot to iteratively design an image prompt. Each follow-up request represents an edit to the previous image.\n"
    "Your task is to compile these editing commands by writing a single, cohesive, highly-detailed image generation prompt representing the updated state of the scene.\n\n"
    "CRITICAL RULES FOR MERGING HISTORY:\n"
    "1. PRESERVE THE SCENE: Do not alter the core subjects, framing, art style, environment, or composition of the previous image description unless the user explicitly requested to change them.\n"
    "2. DIRECT SUBSTITUTION: If the user requests a change of attribute (e.g. changing red hair to blue, changing a sunny day to rain, changing a sports car to a vintage truck), directly swap out the old description phrases with the new ones. Do not just append them as a tag at the end.\n"
    "3. ADDITIONS & DELETIONS: If the user requests to add an object (e.g. 'add a dog'), integrate it naturally into the scene description (e.g. placing the dog next to the subject, details of its appearance, etc.). If they request to remove something, remove its description completely.\n"
    "4. STARTING NEW TOPICS: If the User Input is a completely new prompt that is unrelated to the preceding history, ignore the history and write a brand new detailed prompt from scratch describing subjects, colors, lighting, camera angle, and mood.\n\n"
    "EXAMPLES OF REPHRASING:\n"
    "- Preceding Refined Prompt: 'A detailed digital painting of a cozy log cabin in a snowy pine forest at twilight...'\n"
    "  User Input: 'add a glowing campfire in front'\n"
    "  Result Prompt: 'A detailed digital painting of a cozy log cabin in a snowy pine forest at twilight, with a warm glowing campfire crackling in the front yard casting orange light on the snow...'\n\n"
    "- Preceding Refined Prompt: 'A photorealistic portrait of a young woman with red hair wearing a green sweater...'\n"
    "  User Input: 'make her hair blue and sweater black'\n"
    "  Result Prompt: 'A photorealistic portrait of a young woman with blue hair wearing a black sweater...'\n\n"
    "Do NOT write any introduction, explanations, conversational text, or Markdown formatting. Output ONLY the final refined image prompt."
)

ROUTING_SYSTEM_INSTRUCTION = (
    "You are the orchestrator for a text-to-image chatbot. Your job is to classify the Current User Input and decide how to respond.\n"
    "You must choose one of three actions:\n\n"
    "1. CHITCHAT: ONLY if the user is greeting you (e.g. 'hi', 'hello'), asking how you are (e.g. 'how are you?'), asking how you can help them (e.g. 'what can you do?', 'how can you help me?'), or asking about your identity (e.g. 'who are you?').\n"
    "   - Format your output exactly as: CHITCHAT: [your friendly conversational response here]\n\n"
    "2. CLARIFY: If the user input is NOT one of the approved CHITCHAT topics listed above, AND it does NOT describe a scene or contain any image generation/editing commands (e.g. it is general discussion, a math question, code, writing a poem, telling a joke, or a vague/empty command like 'generate', 'create', 'do it', 'wallpaper', 'make something').\n"
    "   - Format your output exactly as: CLARIFY: Please provide the detailed information about what image you want to generate (specifying subjects, environment, lighting, and style) so I can create it for you.\n\n"
    "3. GENERATE: If the user describes a visual scene to generate, OR provides any follow-up instruction to edit, modify, add, or remove elements in the image (even if very short/simple, e.g., 'add a dog', 'make the car blue', 'add krishna in it', 'change background to night', 'a cute cat').\n"
    "   - Format your output exactly as: GENERATE\n\n"
    "EXAMPLES:\n"
    "- User: 'Hi there!' -> Output: CHITCHAT: Hello! How can I help you visualize your ideas today?\n"
    "- User: 'who are you?' -> Output: CHITCHAT: I am AetherImage Chatbot, your AI image assistant.\n"
    "- User: 'Write a poem about trees.' -> Output: CLARIFY: Please provide the detailed information about what image you want to generate (specifying subjects, environment, lighting, and style) so I can create it for you.\n"
    "- User: 'wallpaper' -> Output: CLARIFY: Please provide the detailed information about what image you want to generate (specifying subjects, environment, lighting, and style) so I can create it for you.\n"
    "- User: 'a cozy cabin' -> Output: GENERATE\n"
    "- User: 'add a dog to the scene' -> Output: GENERATE\n"
    "- User: 'add krishna figure in it' -> Output: GENERATE\n"
    "- User: 'make it blue' -> Output: GENERATE\n\n"
    "Output ONLY the formatted string. Do not add explanations, conversational markdown, or other text."
)

class OllamaService:
    @staticmethod
    async def is_ollama_available() -> bool:
        """
        Checks if the Ollama service is reachable.
        """
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{config.OLLAMA_URL}/api/tags")
                return response.status_code == 200
        except Exception:
            logger.warning(f"Ollama service is not reachable at: {config.OLLAMA_URL}")
            return False

    @staticmethod
    async def refine_prompt(raw_prompt: str, history: list = None) -> str:
        """
        Refines a raw text prompt into a detailed version using the Ollama LLM,
        taking into account conversation history via native Chat API to handle follow-ups.
        """
        if not raw_prompt or not raw_prompt.strip():
            return ""

        available = await OllamaService.is_ollama_available()
        if not available:
            logger.info("Ollama is offline. Skipping prompt refinement, using original prompt.")
            return raw_prompt

        # Format conversation history context into message roles
        messages = [
            {"role": "system", "content": REFINEMENT_SYSTEM_INSTRUCTION}
        ]
        
        if history:
            for msg in history:
                role = msg.get("role", "")
                if role == "user":
                    messages.append({"role": "user", "content": msg.get("content", "")})
                elif role == "assistant":
                    refined = msg.get("refinedPrompt") or msg.get("content")
                    messages.append({"role": "assistant", "content": refined})
                    
        # Append the new user prompt
        messages.append({"role": "user", "content": raw_prompt})

        try:
            logger.info(f"Attempting prompt refinement using Ollama chat model: {config.OLLAMA_REFINEMENT_MODEL}")
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(
                    f"{config.OLLAMA_URL}/api/chat",
                    json={
                        "model": config.OLLAMA_REFINEMENT_MODEL,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 150
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama chat responded with status: {response.status_code}")
                
                data = response.json()
                refined = data.get("message", {}).get("content", "").strip()
                if refined:
                    logger.info(f"Successfully refined prompt: {refined}")
                    return refined
                
                logger.warning("Ollama chat returned empty response for prompt refinement. Using original prompt.")
                return raw_prompt
        except Exception as e:
            logger.error(f"Error during prompt refinement: {e}")
            logger.info("Falling back to original prompt.")
            return raw_prompt

    @staticmethod
    async def refine_via_gemini(raw_prompt: str, history: list, api_key: str) -> str:
        """
        Refines/rephrases the image prompt using Google's Gemini 1.5 Flash model with native structured chat roles.
        """
        logger.info("Refining prompt via Gemini 1.5 Flash Chat...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        contents = []
        if history:
            for msg in history:
                role = msg.get("role", "")
                gemini_role = "user" if role == "user" else "model"
                refined = msg.get("refinedPrompt") or msg.get("content") if role == "assistant" else msg.get("content", "")
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": refined}]
                })
        
        # Append the new user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": raw_prompt}]
        })

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": REFINEMENT_SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 200
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise Exception(f"Gemini Refinement API returned error: {response.text}")
                
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise Exception("No text candidates returned by Gemini Refinement API")
                
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not text:
                    raise Exception("Empty content returned by Gemini Refinement API")
                    
                refined = text.strip()
                logger.info(f"Successfully refined prompt via Gemini: {refined}")
                return refined
        except Exception as e:
            logger.error(f"Error during Gemini prompt refinement: {e}")
            logger.info("Falling back to local Ollama/original prompt.")
            return await OllamaService.refine_prompt(raw_prompt, history)

    @staticmethod
    async def generate_image_directly(prompt: str) -> str:
        """
        Directly requests image generation from Ollama if running a custom image model.
        """
        logger.info(f"Sending direct generation request to Ollama using model: {config.OLLAMA_IMAGE_MODEL}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{config.OLLAMA_URL}/api/generate",
                    json={
                        "model": config.OLLAMA_IMAGE_MODEL,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama direct generation failed with status: {response.status_code}")
                    
                data = response.json()
                if "image" in data:
                    return data["image"]
                elif "response" in data:
                    return data["response"]
                    
                raise Exception("Ollama response did not contain image data")
        except Exception as e:
            logger.error(f"Error during direct Ollama generation: {e}")
            raise e

    @staticmethod
    async def classify_and_route_input(prompt: str, history: list = None) -> dict:
        """
        Classifies the user input into CHITCHAT, CLARIFY, or GENERATE using Ollama.
        """
        messages = [
            {"role": "system", "content": ROUTING_SYSTEM_INSTRUCTION}
        ]
        
        # Add history if available to give context
        if history:
            for msg in history[-5:]:  # Limit to last 5 messages to avoid context bloat
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    # Strip any "Here is your generated image" prefixes to keep history clean
                    if isinstance(content, str) and content.startswith("Here is your generated image"):
                        content = "Here is the image."
                    messages.append({"role": role, "content": content})
                    
        # Append current user prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info("Attempting input routing classification using Ollama model: llama3.2:latest")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{config.OLLAMA_URL}/api/chat",
                    json={
                        "model": "llama3.2:latest",
                        "messages": messages,
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    resp_data = response.json()
                    raw_reply = resp_data["message"]["content"].strip()
                    logger.info(f"Ollama routing classification result: {raw_reply}")
                    
                    if raw_reply.startswith("CHITCHAT:"):
                        return {"action": "chitchat", "message": raw_reply[9:].strip()}
                    elif raw_reply.startswith("CLARIFY:"):
                        return {"action": "clarify", "message": raw_reply[8:].strip()}
                    elif raw_reply.startswith("GENERATE"):
                        return {"action": "generate"}
                    
                    # Fallback if LLM deviates but outputs conversational text
                    if len(raw_reply) > 20 and not any(k in raw_reply.lower() for k in ["generate", "draw", "create", "make"]):
                        return {"action": "chitchat", "message": raw_reply}
                        
        except Exception as e:
            logger.error(f"Error during input classification: {e}")
            
        # Fallback to generate if LLM errors or is unavailable
        return {"action": "generate"}
