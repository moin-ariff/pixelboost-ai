FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir setuptools==59.6.0 && \
    pip install --no-cache-dir "nvidia-cublas==13.1.0.3.*" && \
    pip install --no-cache-dir -r requirements.txt
    
# Copy project files
COPY . .

# Create necessary folders
RUN mkdir -p uploads outputs

# Expose port
EXPOSE 7860

# Run app
CMD ["python", "app.py"]