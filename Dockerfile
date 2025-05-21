FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/sample_data
RUN mkdir -p /app/frontend/public/logos
RUN mkdir -p /app/frontend/fonts
RUN mkdir -p /app/cache

# Create a basic logo if it doesn't exist
RUN echo "Creating placeholder logo" && \
    python -c "from PIL import Image, ImageDraw, ImageFont; img = Image.new('RGB', (200, 100), color=(255, 255, 255)); draw = ImageDraw.Draw(img); img.save('frontend/public/logos/logo.png')"

# Expose port for Streamlit
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Command to run the application
CMD ["streamlit", "run", "streamlit_app.py"]