FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libfreetype6 \
    libffi-dev \
    libjpeg62-turbo \
    libpng16-16 \
    zlib1g \
    pngquant \
    && rm -rf /var/lib/apt/lists/*

# Install mkdocs-material with imaging support
RUN pip install "mkdocs-material[imaging]"

WORKDIR /docs

# Copy the project files
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run mkdocs
CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]