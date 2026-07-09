import asyncio
import httpx
from main import app

async def run_tests():
    # We use httpx's ASGITransport to test our FastAPI routes in-memory
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("1. Testing GET /api/status endpoint...")
        res_status = await client.get("/api/status")
        
        assert res_status.status_code == 200, f"Status route failed with code {res_status.status_code}"
        data_status = res_status.json()
        assert data_status["success"] is True, "Status endpoint did not return success=True"
        assert "ollama" in data_status, "Ollama metadata missing in status response"
        assert "generator" in data_status, "Generator metadata missing in status response"
        
        print(f"  [OK] /api/status passed!")
        print(f"    - Ollama Available: {data_status['ollama']['available']}")
        print(f"    - Generation Provider: {data_status['generator']['provider']}")

        print("\n2. Testing POST /api/generate endpoint with history, model routing, & seed consistency...")
        # Verify history validation, refinement, model selection, and seed locking
        test_payload = {
            "prompt": "make it blue",
            "refine": True,
            "model": "ideogram-v4-quality",
            "seed": 987654,
            "history": [
                {"role": "user", "content": "a sports car"},
                {"role": "assistant", "content": "Here is your generated image...", "refinedPrompt": "A sleek red sports car parked on a grid road during sunset"}
            ]
        }
        res_gen = await client.post("/api/generate", json=test_payload)

        
        assert res_gen.status_code == 200, f"Generate route failed with code {res_gen.status_code}"
        data_gen = res_gen.json()
        assert data_gen["success"] is True, "Generate endpoint did not return success=True"
        
        gen_data = data_gen["data"]
        assert "image" in gen_data, "Generated image data missing in response"
        assert "source" in gen_data, "Generator source missing in response"
        assert "duration" in gen_data, "Duration metric missing in response"
        assert "seed" in gen_data, "Seed missing in response"
        assert gen_data["seed"] == 987654, f"Returned seed {gen_data['seed']} does not match input 987654"
        assert gen_data["image"].startswith("data:image/"), "Returned image is not a valid base64 data URI"
        
        print(f"  [OK] /api/generate passed!")
        print(f"    - Image Source: {gen_data['source']}")
        print(f"    - Seed consistency: {gen_data['seed']}")
        print(f"    - Execution Latency: {gen_data['duration']}ms")

        print("\n3. Testing POST /api/generate with Gemini Model (expecting error due to missing API key)...")
        gemini_payload = {
            "prompt": "A photorealistic close-up photo of a vibrant red rose covered in sparkling morning dew drops, cinematic lighting",
            "model": "gemini-3.1-flash-image",
            "refine": False
        }
        res_gemini = await client.post("/api/generate", json=gemini_payload)
        assert res_gemini.status_code == 400, f"Expected 400 Bad Request, got {res_gemini.status_code}"
        data_gemini = res_gemini.json()
        assert "Gemini API Key is required" in data_gemini["detail"], f"Unexpected error message: {data_gemini['detail']}"
        print("  [OK] /api/generate Gemini key validation passed!")



if __name__ == "__main__":
    print("==================================================")
    print(" Starting FastAPI Backend Verification Tests...")
    print("==================================================")
    
    try:
        asyncio.run(run_tests())
        print("\n==================================================")
        print(" ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("==================================================")
    except Exception as e:
        print("\n==================================================")
        print(f" VERIFICATION TEST FAILED: {e}")
        print("==================================================")
        import sys
        sys.exit(1)
