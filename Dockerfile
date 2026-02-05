# Use Python 3.11 slim image
FROM python:3.11-slim

# Install Node.js for building frontend
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files first (for caching)
COPY web-app/package*.json ./web-app/

# Install Node dependencies
WORKDIR /app/web-app
RUN npm install

# Copy Python requirements
COPY web-app/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
WORKDIR /app
COPY . .

# Build React frontend
WORKDIR /app/web-app
RUN npm run build

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV FLASK_ENV=production

# Start the application
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "flask_api:app", "--bind", "0.0.0.0:8080"]
