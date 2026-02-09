FROM python:3.10-alpine

WORKDIR /app

# Install git
RUN apk add --no-cache git

# Install system dependencies (git for cloning, ffmpeg for audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Clone the repo
RUN git clone https://github.com/Ranjan-Shettigar/YTAV.git /app


# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 5000

# Run the app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
