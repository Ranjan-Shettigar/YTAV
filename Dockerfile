FROM python:3.10-alpine

# Install git
RUN apk add --no-cache git

# Clone the repo
RUN git clone https://github.com/Ranjan-Shettigar/YTAV.git /app

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 5000

# Run the app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
