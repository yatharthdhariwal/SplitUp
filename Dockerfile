# -----------------------------------------------------------------------
# Dockerfile for SplitWise Clone (Flask API)
# -----------------------------------------------------------------------
# Build:   docker build -t splitwise-clone .
# Run:     docker compose up   (preferred — uses docker-compose.yml)
# -----------------------------------------------------------------------

# Use the official slim Python image.
# "slim" strips unnecessary OS packages → smaller image (~150MB vs ~900MB).
# Pin the version so builds are reproducible.
FROM python:3.11-slim

# Set the working directory inside the container.
# All subsequent commands run relative to this path.
WORKDIR /app

# WHY copy requirements.txt first?
# Docker builds in layers. If requirements.txt hasn't changed, Docker
# reuses the cached pip install layer — much faster rebuilds.
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir: don't store pip's download cache inside the image (saves space).
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the application code.
# This happens AFTER pip install so code changes don't bust the pip cache.
COPY . .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Tell Docker this container listens on port 8000.
# This is documentation — the actual port binding happens in docker-compose.yml.
EXPOSE 8000

# Set the default environment to production.
# Can be overridden in docker-compose.yml or the hosting platform.
ENV FLASK_ENV=production

# Run the entrypoint script when the container starts.
# It applies migrations then starts gunicorn.
ENTRYPOINT ["./entrypoint.sh"]
