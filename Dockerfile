FROM python:3.11-slim

WORKDIR /app

# Install system deps (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

# Default port used by many hosts; Vercel will provide a PORT env var to the container
ENV PORT=8080
EXPOSE 8080

# Start Streamlit on the provided port
CMD ["bash","-lc","streamlit run dashboard/app.py --server.port ${PORT} --server.address 0.0.0.0"]
