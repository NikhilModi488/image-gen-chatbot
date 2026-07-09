from typing import Optional, Any
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.services.image_service import ImageService

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The text prompt to generate an image for")
    refine: bool = Field(default=False, description="Whether to refine prompt with Ollama LLM")
    history: Optional[list[dict[str, Any]]] = Field(default=None, description="Previous messages in the conversation")
    model: Optional[str] = Field(default=None, description="The image generation model to use")
    geminiApiKey: Optional[str] = Field(default=None, description="The Google Gemini API Key for Imagen 3")
    seed: Optional[int] = Field(default=None, description="Optional seed for generation consistency")

class ImageController:
    @staticmethod
    async def generate(request: GenerateRequest) -> dict:
        """
        Validates request model and executes the image generation service.
        """
        try:
            result = await ImageService.generate_image(
                prompt=request.prompt,
                refine=request.refine,
                history=request.history,
                model=request.model,
                gemini_api_key=request.geminiApiKey,
                seed=request.seed
            )




            return {
                "success": True,
                "data": result
            }
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

    @staticmethod
    async def status() -> dict:
        """
        Returns connection and backend status details.
        """
        from app.services.ollama_service import OllamaService
        from app.config import config
        
        ollama_active = await OllamaService.is_ollama_available()
        return {
            "success": True,
            "ollama": {
                "available": ollama_active,
                "refinementModel": config.OLLAMA_REFINEMENT_MODEL,
                "imageModel": config.OLLAMA_IMAGE_MODEL,
                "defaultRefinementEnabled": config.USE_OLLAMA_PROMPT_REFINEMENT
            },
            "generator": {
                "provider": config.IMAGE_GENERATOR_PROVIDER
            }
        }

