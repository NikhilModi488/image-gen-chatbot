import { config } from '../../config/config.js';
import { OllamaService } from './ollamaService.js';

export class GeneratorService {
  /**
   * Generates an image based on the prompt, utilizing configured provider and fallbacks.
   * @param {string} prompt - The refined descriptive prompt.
   * @returns {Promise<{ image: string, source: string }>} Base64 image string (or data URL) and the source provider.
   */
  static async generateImage(prompt) {
    const provider = config.generator.provider;
    console.log(`Starting image generation with primary provider: ${provider}`);

    // Order of execution depends on primary provider
    if (provider === 'ollama') {
      try {
        const image = await OllamaService.generateImageDirectly(prompt);
        return { image, source: 'Ollama Local' };
      } catch (error) {
        console.error('Ollama generation failed, falling back to Pollinations AI. Error:', error.message);
        // Fall through to next provider
      }
    }

    if (provider === 'ollama' || provider === 'pollinations') {
      try {
        const image = await this.generateViaPollinations(prompt);
        return { image, source: 'Pollinations AI (Online)' };
      } catch (error) {
        console.error('Pollinations AI generation failed, falling back to Local SVG Mock. Error:', error.message);
        // Fall through to local-mock
      }
    }

    // Default / Final fallback: Local SVG Mockup
    const image = this.generateLocalMockSvg(prompt);
    return { image, source: 'Local Offline Engine (Mockup)' };
  }

  /**
   * Generates an image using Pollinations AI and converts it to Base64.
   * @param {string} prompt - The text prompt.
   * @returns {Promise<string>} Base64 image data URL.
   */
  static async generateViaPollinations(prompt) {
    console.log('Sending request to Pollinations AI...');
    const encodedPrompt = encodeURIComponent(prompt);
    
    // We add seed/random variables to prevent caching and get distinct images
    const randomSeed = Math.floor(Math.random() * 1000000);
    const url = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=800&height=600&nologo=true&private=true&seed=${randomSeed}`;

    const response = await fetch(url, {
      signal: AbortSignal.timeout(15000), // 15s timeout
    });

    if (!response.ok) {
      throw new Error(`Pollinations AI responded with status: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    const mimeType = response.headers.get('content-type') || 'image/jpeg';
    const base64Image = buffer.toString('base64');
    
    return `data:${mimeType};base64,${base64Image}`;
  }

  /**
   * Generates a beautiful SVG gradient placeholder with the prompt text.
   * Runs completely offline with zero dependencies.
   * @param {string} prompt - The text prompt.
   * @returns {string} Base64 SVG data URL.
   */
  static generateLocalMockSvg(prompt) {
    console.log('Generating local SVG mockup...');
    
    // Wrap the text so it fits within the card container
    const words = prompt.split(' ');
    const lines = [];
    let currentLine = '';
    
    for (const word of words) {
      // Maximum characters per line
      if ((currentLine + ' ' + word).length > 35) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = currentLine ? currentLine + ' ' + word : word;
      }
    }
    if (currentLine) {
      lines.push(currentLine);
    }

    // Limit to max 6 lines for spacing
    const displayLines = lines.slice(0, 6);
    const textElements = displayLines.map((line, idx) => {
      // Calculate vertical offset relative to middle
      const yOffset = 50 - (displayLines.length - 1) * 3.5 + idx * 7.5;
      return `<text x="50%" y="${yOffset}%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-family="'Outfit', 'Inter', sans-serif" font-size="20px" font-weight="500">${this.escapeXml(line)}</text>`;
    }).join('\n');

    // Selection of vibrant gradients
    const gradients = [
      { start: '#8A2387', end: '#E94057' }, // Purple to Red-Orange
      { start: '#00F2FE', end: '#4FACFE' }, // Cyan to Blue
      { start: '#11998E', end: '#38EF7D' }, // Teal to Light Green
      { start: '#FC466B', end: '#3F5EFB' }, // Pink to Blue
      { start: '#F27121', end: '#E94057' }, // Dark Orange to Red
      { start: '#7F00FF', end: '#FF007F' }  // Purple to Magenta
    ];

    // Select gradient based on prompt hash code to be deterministic yet varied
    let hash = 0;
    for (let i = 0; i < prompt.length; i++) {
      hash = prompt.charCodeAt(i) + ((hash << 5) - hash);
    }
    const gradientIndex = Math.abs(hash) % gradients.length;
    const selectedGrad = gradients[gradientIndex];

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
        <defs>
          <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:${selectedGrad.start};stop-opacity:1" />
            <stop offset="100%" style="stop-color:${selectedGrad.end};stop-opacity:1" />
          </linearGradient>
          <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="15" stdDeviation="20" flood-color="#000000" flood-opacity="0.45"/>
          </filter>
        </defs>
        
        <!-- Background dark canvas -->
        <rect width="100%" height="100%" fill="#0a0b10" />
        
        <!-- Decorative abstract ambient light spots -->
        <circle cx="20%" cy="20%" r="250" fill="${selectedGrad.start}" opacity="0.15" filter="blur(80px)" />
        <circle cx="80%" cy="80%" r="300" fill="${selectedGrad.end}" opacity="0.12" filter="blur(100px)" />
        
        <!-- Main dynamic gradient card with drop shadow -->
        <rect x="80" y="80" width="640" height="440" rx="24" fill="url(#cardGrad)" filter="url(#cardShadow)" />
        
        <!-- Inner glassmorphic overlay for the card -->
        <rect x="80" y="80" width="640" height="440" rx="24" fill="#000000" opacity="0.15" />
        <rect x="80" y="80" width="640" height="440" rx="24" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.25" />
        
        <!-- Card Text Elements -->
        <text x="50%" y="22%" dominant-baseline="middle" text-anchor="middle" fill="#FFFFFF" font-family="'Outfit', 'Inter', sans-serif" font-size="14px" font-weight="700" letter-spacing="4px" opacity="0.75">AI GENERATED PREVIEW</text>
        
        <!-- Rendered lines of the prompt -->
        <g>
          ${textElements}
        </g>
        
        <!-- Bottom technical specs -->
        <text x="50%" y="82%" dominant-baseline="middle" text-anchor="middle" fill="#FFFFFF" font-family="'Outfit', 'Inter', sans-serif" font-size="11px" font-weight="600" letter-spacing="1px" opacity="0.6">
          OFFLINE FALLBACK ENGINE • ACTIVE
        </text>
        
        <!-- Outer border styling -->
        <rect x="20" y="20" width="760" height="560" rx="16" fill="none" stroke="#1d2030" stroke-width="2" />
        <circle cx="35" cy="35" r="5" fill="#ef4444" />
        <circle cx="50" cy="35" r="5" fill="#f59e0b" />
        <circle cx="65" cy="35" r="5" fill="#10b981" />
        <text x="765" y="40" text-anchor="end" fill="#4b5563" font-family="monospace" font-size="10px">SYSTEM: OK</text>
      </svg>
    `;

    return `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`;
  }

  /**
   * Escapes XML characters to prevent SVG syntax errors.
   */
  static escapeXml(unsafe) {
    return unsafe.replace(/[<>&'"]/g, (c) => {
      switch (c) {
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '&': return '&amp;';
        case '\'': return '&apos;';
        case '"': return '&quot;';
        default: return c;
      }
    });
  }
}
