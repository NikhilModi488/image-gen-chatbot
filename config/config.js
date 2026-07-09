import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// Load environmental variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const config = {
  port: parseInt(process.env.PORT || '3000', 10),
  ollama: {
    url: process.env.OLLAMA_URL || 'http://localhost:11434',
    refinementModel: process.env.OLLAMA_REFINEMENT_MODEL || 'llama3',
    imageModel: process.env.OLLAMA_IMAGE_MODEL || 'stable-diffusion',
    useOllamaPromptRefinement: process.env.USE_OLLAMA_PROMPT_REFINEMENT === 'true',
  },
  generator: {
    provider: process.env.IMAGE_GENERATOR_PROVIDER || 'pollinations', // 'ollama', 'pollinations', 'local-mock'
  },
  publicPath: path.join(__dirname, '../public'),
};
