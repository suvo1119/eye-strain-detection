# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements first
COPY web-app/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json for npm install
COPY web-app/package*.json ./web-app/

# Install Node dependencies
WORKDIR /app/web-app
RUN npm install

# Copy all source code
WORKDIR /app
COPY . .

# Build React frontend
WORKDIR /app/web-app
RUN npm run build

# Set environment variables
ENV PORT=10000
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port (Render uses 10000 by default)
EXPOSE 10000

# Start the application
CMD ["python", "start.py"]
