FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

# Copy only requirements first (better caching)
COPY requirements.txt .

# Install dependencies into system Python
RUN uv pip install --system -r requirements.txt

# Copy rest of the app
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]