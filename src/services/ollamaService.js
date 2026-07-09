import { config } from '../../config/config.js';

export class OllamaService {
  /**
   * Checks if the Ollama service is reachable.
   * @returns {Promise<boolean>} True if reachable, false otherwise.
   */
  static async isOllamaAvailable() {
    try {
      const response = await fetch(`${config.ollama.url}/api/tags`, {
        signal: AbortSignal.timeout(2000), // Timeout after 2 seconds
      });
      return response.ok;
    } catch (error) {
      console.warn('Ollama service is not reachable at:', config.ollama.url);
      return false;
    }
  }

  /**
   * Refines a raw text prompt into a detailed version using Ollama LLM.
   * @param {string} rawPrompt - The raw prompt from the user.
   * @returns {Promise<string>} The refined, descriptive prompt.
   */
  static async refinePrompt(rawPrompt) {
    if (!rawPrompt || rawPrompt.trim() === '') {
      return '';
    }

    const available = await this.isOllamaAvailable();
    if (!available) {
      console.log('Ollama is unavailable. Skipping prompt refinement, using original prompt.');
      return rawPrompt;
    }

    const systemPrompt = `You are an expert prompt engineer for text-to-image models like Stable Diffusion, Midjourney, and DALL-E. 
Your task is to expand the user's simple input prompt into a highly descriptive, visually rich prompt.
Describe the environment, subject details, camera angle, lighting (e.g., volumetric light, cinematic, golden hour), colors, mood, and art style (e.g., photorealistic, digital painting, oil sketch).
Do NOT include any introduction, explanations, markdown formatting, or conversational text. Output ONLY the final enhanced prompt.

Example:
Input: "a cozy cabin"
Output: "A rustic, cozy log cabin nestled in a snowy pine forest during twilight, smoke curling from the chimney, warm golden light spilling from the windows, soft focus, high-detailed digital painting, cinematic lighting, 8k resolution"

Input: "${rawPrompt}"
Output:`;

    try {
      console.log(`Attempting to refine prompt using Ollama model: ${config.ollama.refinementModel}`);
      const response = await fetch(`${config.ollama.url}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: config.ollama.refinementModel,
          prompt: systemPrompt,
          stream: false,
          options: {
            temperature: 0.7,
            num_predict: 100, // Limit response length
          }
        }),
        signal: AbortSignal.timeout(10000), // 10s timeout for refinement
      });

      if (!response.ok) {
        throw new Error(`Ollama prompt refinement failed with status: ${response.status}`);
      }

      const data = await response.json();
      const refined = data.response?.trim();

      if (refined) {
        console.log('Successfully refined prompt via Ollama:', refined);
        return refined;
      }
      
      console.warn('Ollama returned empty response for prompt refinement. Using original prompt.');
      return rawPrompt;
    } catch (error) {
      console.error('Error during prompt refinement:', error.message);
      console.log('Falling back to original prompt.');
      return rawPrompt;
    }
  }

  /**
   * Directly requests image generation from Ollama if running a custom image model.
   * @param {string} prompt - The refined prompt.
   * @returns {Promise<string>} Base64 image data.
   */
  static async generateImageDirectly(prompt) {
    console.log(`Sending image generation request directly to Ollama using model: ${config.ollama.imageModel}`);
    
    // Note: This matches standard Ollama structures if they have an experimental/custom endpoint
    // or if the user is running an image generation adapter.
    const response = await fetch(`${config.ollama.url}/api/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: config.ollama.imageModel,
        prompt: prompt,
        stream: false,
        // Custom models might return base64 images inside JSON format or binary stream
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama direct generation failed with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Typically direct image models return base64 data. We inspect common response keys.
    if (data.image) {
      return data.image; // Already base64 or url
    } else if (data.response) {
      // If it returns base64 inside the response text
      return data.response;
    }
    
    throw new Error('Ollama response did not contain image data');
  }
}
