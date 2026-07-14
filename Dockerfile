FROM python:3.10-slim

# Install curl, zstd, and system dependencies
RUN apt-get update && apt-get install -y curl zstd && rm -rf /var/lib/apt/lists/*

# Install Ollama engine binary
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (7860 for Hugging Face Spaces default)
EXPOSE 7860

# Set environment defaults
ENV PORT=7860
ENV OLLAMA_URL=http://localhost:11434
ENV USE_OLLAMA_PROMPT_REFINEMENT=True

# Make startup script executable
RUN chmod +x start.sh

# Run the startup script
CMD ["./start.sh"]
