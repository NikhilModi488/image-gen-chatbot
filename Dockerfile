FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 3000

# Set environment defaults
ENV PORT=3000
ENV OLLAMA_URL=http://ollama:11434
ENV USE_OLLAMA_PROMPT_REFINEMENT=True

# Run the application
CMD ["python", "main.py"]
