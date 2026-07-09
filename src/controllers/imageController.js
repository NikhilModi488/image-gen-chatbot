import { ImageService } from '../services/imageService.js';

export class ImageController {
  /**
   * Handles the text-to-image generation request.
   * POST /api/generate
   */
  static async generate(req, res) {
    try {
      const { prompt, refine } = req.body;

      // Request validation
      if (!prompt || typeof prompt !== 'string' || prompt.trim() === '') {
        return res.status(400).json({
          success: false,
          error: 'Missing or invalid "prompt" parameter. Prompt must be a non-empty string.',
        });
      }

      console.log(`Received generation request. Prompt: "${prompt}" (Refine: ${refine === true})`);

      // Invoke the service layer
      const result = await ImageService.generateImage({
        prompt,
        refine: refine === true
      });

      // Send successful response
      return res.status(200).json({
        success: true,
        data: result
      });

    } catch (error) {
      console.error('Error in ImageController.generate:', error);
      return res.status(500).json({
        success: false,
        error: error.message || 'An error occurred during image generation.',
      });
    }
  }
}
