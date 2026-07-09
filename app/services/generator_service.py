import base64
import random
import urllib.parse
import httpx
import logging
from app.config import config
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

class GeneratorService:
    @staticmethod
    async def generate_image(prompt: str, model: str = None, gemini_api_key: str = None, seed: int = None) -> dict:
        """
        Generates an image using the primary provider with fallback support.
        """
        # If the user explicitly selected Gemini, route it to Google Gemini Imagen 3
        if model == "gemini-3.1-flash-image":
            if not gemini_api_key or not gemini_api_key.strip():
                raise ValueError("Gemini API Key is required to use the Gemini 3.1 Flash Image model.")
            try:
                image_data = await GeneratorService.generate_via_gemini(prompt, gemini_api_key, seed)
                return {"image": image_data, "source": "Gemini 3.1 Flash Image (Imagen 3)"}
            except Exception as e:
                logger.error(f"Gemini generation failed, falling back to Pollinations AI. Error: {e}")

        provider = config.IMAGE_GENERATOR_PROVIDER
        logger.info(f"Starting image generation with primary provider: {provider}")

        # 1. Attempt Ollama if configured as primary
        if provider == "ollama":
            try:
                image_data = await OllamaService.generate_image_directly(prompt)
                return {"image": image_data, "source": "Ollama Local"}
            except Exception as e:
                logger.error(f"Ollama generation failed, falling back to Pollinations AI. Error: {e}")

        # 2. Attempt Pollinations AI (online generator)
        if provider in ["ollama", "pollinations"]:
            try:
                image_data = await GeneratorService.generate_via_pollinations(prompt, model, seed)
                # Show the specific model name in the source description
                source_name = f"Pollinations AI ({model if model else config.ollama.imageModel})"
                return {"image": image_data, "source": source_name}
            except Exception as e:
                logger.error(f"Pollinations AI generation failed, falling back to LoremFlickr. Error: {e}")

        # 3. Attempt LoremFlickr (online real photo search fallback)
        try:
            image_data = await GeneratorService.generate_via_loremflickr(prompt)
            return {"image": image_data, "source": "LoremFlickr Photo Search"}
        except Exception as e:
            logger.error(f"LoremFlickr photo retrieval failed, falling back to Local SVG Mock. Error: {e}")

        # 4. Offline fallback
        image_data = GeneratorService.generate_local_mock_svg(prompt)
        return {"image": image_data, "source": "Local Offline Engine (Mockup)"}

    @staticmethod
    async def generate_via_pollinations(prompt: str, model: str = None, seed: int = None) -> str:
        """
        Generates an image via the Pollinations AI free API and encodes it to base64.
        Includes a retry mechanism for rate limits (429) and ignores SSL checks.
        """
        import asyncio
        logger.info(f"Sending request to Pollinations AI (Model: {model}, Seed: {seed})...")
        encoded_prompt = urllib.parse.quote(prompt)
        
        max_attempts = 3
        delay_seconds = 4.0
        
        active_model = model if model else config.ollama.imageModel
        active_seed = seed if seed is not None else random.randint(1, 1000000)
        
        # verify=False is critical to bypass corporate/local SSL certificate handshake failures
        async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
            for attempt in range(1, max_attempts + 1):
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true&seed={active_seed}&model={active_model}"

                
                try:
                    logger.info(f"Pollinations AI request attempt {attempt} of {max_attempts}...")
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "image/jpeg")
                        binary_data = response.content
                        base64_image = base64.b64encode(binary_data).decode("utf-8")
                        return f"data:{content_type};base64,{base64_image}"
                        
                    elif response.status_code == 429:
                        logger.warn(f"Pollinations AI rate limited (429: Queue full). Retrying in {delay_seconds}s...")
                        await asyncio.sleep(delay_seconds)
                        delay_seconds *= 1.5 # simple backoff
                        
                    else:
                        raise Exception(f"Pollinations AI responded with status: {response.status_code}")
                        
                except httpx.RequestError as e:
                    if attempt == max_attempts:
                        raise Exception(f"Network error connecting to Pollinations AI: {e}")
                    logger.warn(f"Network error (attempt {attempt}): {e}. Retrying...")
                    await asyncio.sleep(delay_seconds)
                    
        raise Exception("Failed to generate image after maximum attempts")

    @staticmethod
    async def generate_via_gemini(prompt: str, api_key: str, seed: int = None) -> str:
        """
        Generates an image using Google's Imagen 3 model via Google Gemini Developer API.
        """
        logger.info(f"Sending request to Google Gemini Imagen 3 API (Seed: {seed})...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
        
        params = {
            "sampleCount": 1,
            "aspectRatio": "4:3",
            "outputMimeType": "image/jpeg"
        }
        if seed is not None:
            params["seed"] = seed

        payload = {
            "instances": [
                {
                    "prompt": prompt
                }
            ],
            "parameters": params
        }
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", response.text)
                except Exception:
                    pass
                raise Exception(f"Gemini API returned error: {error_detail}")
                
            data = response.json()
            predictions = data.get("predictions", [])
            if not predictions:
                raise Exception("No predictions returned by Gemini API")
                
            image_bytes_b64 = predictions[0].get("bytesBase64Encoded", "")
            if not image_bytes_b64:
                raise Exception("Image bytes empty in Gemini response")
                
            return f"data:image/jpeg;base64,{image_bytes_b64}"


    @staticmethod
    async def generate_via_loremflickr(prompt: str) -> str:
        """
        Fetches a real stock image matching the prompt keywords as a backup online provider.
        Bypasses AI generation queues by doing keyword-based search.
        """
        logger.info("Falling back to LoremFlickr for a real image matching keywords...")
        import re
        # Extract alphanumeric words
        words = re.findall(r'\b\w+\b', prompt.lower())
        # Filter out common stopwords
        stopwords = {
            "a", "an", "the", "in", "on", "at", "and", "or", "of", "with", "for", 
            "style", "digital", "art", "illustration", "highly", "detailed", "painting",
            "cozy", "cute", "beautiful", "sunset", "futuristic", "neon", "realistic"
        }
        keywords = [w for w in words if w not in stopwords]
        
        if not keywords:
            keywords = ["scenery"]
            
        clean_keywords = ",".join(keywords[:4]) # Limit to top 4 keywords
        url = f"https://loremflickr.com/800/600/{clean_keywords}"
        logger.info(f"LoremFlickr URL: {url}")
        
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code != 200:
                raise Exception(f"LoremFlickr responded with status: {response.status_code}")
                
            content_type = response.headers.get("content-type", "image/jpeg")
            binary_data = response.content
            base64_image = base64.b64encode(binary_data).decode("utf-8")
            return f"data:{content_type};base64,{base64_image}"



    @staticmethod
    def generate_local_mock_svg(prompt: str) -> str:
        """
        Generates a beautiful SVG preview with the prompt text overlaying a vibrant gradient.
        No external dependencies, runs offline.
        """
        logger.info("Generating local SVG mockup...")
        
        # Word wrapping logic for SVG
        words = prompt.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) > 35:
                lines.append(current_line)
                current_line = word
            else:
                current_line = (current_line + " " + word) if current_line else word
        if current_line:
            lines.append(current_line)

        # Slice to max 6 lines to fit card
        display_lines = lines[:6]
        text_elements = []
        
        for idx, line in enumerate(display_lines):
            # Vertical centering calculations
            y_offset = 50 - (len(display_lines) - 1) * 3.5 + idx * 7.5
            escaped_line = GeneratorService._escape_xml(line)
            text_elements.append(
                f'<text x="50%" y="{y_offset}%" dominant-baseline="middle" text-anchor="middle" '
                f'fill="#ffffff" font-family="\'Outfit\', \'Inter\', sans-serif" font-size="20px" '
                f'font-weight="500">{escaped_line}</text>'
            )
            
        text_elements_str = "\n            ".join(text_elements)

        # Design gradients
        gradients = [
            {"start": "#8A2387", "end": "#E94057"}, # Purple-Red
            {"start": "#00F2FE", "end": "#4FACFE"}, # Cyan-Blue
            {"start": "#11998E", "end": "#38EF7D"}, # Teal-Green
            {"start": "#FC466B", "end": "#3F5EFB"}, # Pink-Blue
            {"start": "#F27121", "end": "#E94057"}, # Orange-Red
            {"start": "#7F00FF", "end": "#FF007F"}  # Violet-Magenta
        ]

        # Pick gradient deterministically using prompt hash code
        prompt_hash = hash(prompt)
        gradient_index = abs(prompt_hash) % len(gradients)
        selected_grad = gradients[gradient_index]

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
          <defs>
            <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:{selected_grad['start']};stop-opacity:1" />
              <stop offset="100%" style="stop-color:{selected_grad['end']};stop-opacity:1" />
            </linearGradient>
            <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="15" stdDeviation="20" flood-color="#000000" flood-opacity="0.45"/>
            </filter>
          </defs>
          
          <!-- Background -->
          <rect width="100%" height="100%" fill="#0a0b10" />
          
          <!-- Blurred glow ambient circles -->
          <circle cx="20%" cy="20%" r="250" fill="{selected_grad['start']}" opacity="0.15" filter="blur(80px)" />
          <circle cx="80%" cy="80%" r="300" fill="{selected_grad['end']}" opacity="0.12" filter="blur(100px)" />
          
          <!-- Main visual card -->
          <rect x="80" y="80" width="640" height="440" rx="24" fill="url(#cardGrad)" filter="url(#cardShadow)" />
          
          <!-- Card glassmorphism overlays -->
          <rect x="80" y="80" width="640" height="440" rx="24" fill="#000000" opacity="0.15" />
          <rect x="80" y="80" width="640" height="440" rx="24" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.25" />
          
          <!-- Header title -->
          <text x="50%" y="22%" dominant-baseline="middle" text-anchor="middle" fill="#FFFFFF" font-family="'Outfit', 'Inter', sans-serif" font-size="14px" font-weight="700" letter-spacing="4px" opacity="0.75">AI GENERATED PREVIEW</text>
          
          <!-- Prompt text lines -->
          <g>
            {text_elements_str}
          </g>
          
          <!-- Bottom watermark -->
          <text x="50%" y="82%" dominant-baseline="middle" text-anchor="middle" fill="#FFFFFF" font-family="'Outfit', 'Inter', sans-serif" font-size="11px" font-weight="600" letter-spacing="1px" opacity="0.6">
            OFFLINE FALLBACK ENGINE • ACTIVE
          </text>
          
          <!-- Outer border decoration -->
          <rect x="20" y="20" width="760" height="560" rx="16" fill="none" stroke="#1d2030" stroke-width="2" />
          <circle cx="35" cy="35" r="5" fill="#ef4444" />
          <circle cx="50" cy="35" r="5" fill="#f59e0b" />
          <circle cx="65" cy="35" r="5" fill="#10b981" />
          <text x="765" y="40" text-anchor="end" fill="#4b5563" font-family="monospace" font-size="10px">SYSTEM: OK</text>
        </svg>"""
        
        base64_svg = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{base64_svg}"

    @staticmethod
    def _escape_xml(unsafe: str) -> str:
        """
        Escapes XML characters to prevent SVG rendering crashes.
        """
        return (unsafe
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))
