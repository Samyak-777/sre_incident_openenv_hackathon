FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user (Standard for HF Spaces)
RUN useradd -m -u 1000 user
USER user

# Copy application code
COPY --chown=user:user . .

# Ensure server package is in PATH
ENV PYTHONPATH="/app"
ENV PORT=7860
EXPOSE 7860

# Command to run the FastAPI app via the server module
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
