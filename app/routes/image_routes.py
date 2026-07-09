from fastapi import APIRouter
from app.controllers.image_controller import ImageController, GenerateRequest

router = APIRouter(prefix="/api")

@router.post("/generate")
async def generate_image_endpoint(request: GenerateRequest):
    """
    Endpoint for text-to-image generation.
    """
    return await ImageController.generate(request)

@router.get("/status")
async def get_status_endpoint():
    """
    Endpoint to fetch connection and service status.
    """
    return await ImageController.status()

