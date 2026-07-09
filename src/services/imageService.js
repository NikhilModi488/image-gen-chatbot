import { OllamaService } from './ollamaService.js';
import { GeneratorService } from './generatorService.js';
import { config } from '../../config/config.js';

export class ImageService {
  /**
   * Orchestrates prompt refinement and image generation.
   * @param {Object} params - Generation parameters.
   * @param {string} params.prompt - The input raw prompt from the user.
   * @param {boolean} [params.refine=false] - Whether to use Ollama to refine the prompt.
   * @returns {Promise<Object>} Object containing the original prompt, refined prompt, image data, provider source, and execution duration.
   */
  static async generateImage({ prompt, refine = false }) {
    if (!prompt || prompt.trim() === '') {
      throw new Error('Prompt is required');
    }

    const startTime = Date.now();
    let finalPrompt = prompt.trim();
    let refinedPrompt = null;

    // 1. Optional Prompt Refinement via Ollama
    const shouldRefine = refine || config.ollama.useOllamaPromptRefinement;
    if (shouldRefine) {
      try {
        console.log('Initiating prompt refinement...');
        refinedPrompt = await OllamaService.refinePrompt(finalPrompt);
        finalPrompt = refinedPrompt;
      } catch (error) {
        console.error('Prompt refinement failed, using raw prompt:', error.message);
      }
    }

    // 2. Generate Image via the generator service
    console.log(`Generating image for: "${finalPrompt}"`);
    const { image, source } = await GeneratorService.generateImage(finalPrompt);
    
    const duration = Date.now() - startTime;
    console.log(`Generation completed in ${duration}ms via ${source}`);

    return {
      originalPrompt: prompt,
      refinedPrompt: refinedPrompt,
      image: image, // Base64 data URI
      source: source,
      duration: duration
    };
  }
}
