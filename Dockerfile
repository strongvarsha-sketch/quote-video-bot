FROM python:3.11-slim

# ffmpeg is needed to build the videos.
# fonts-dejavu-core covers English captions; fonts-noto-core adds Devanagari (Hindi) support.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-noto-core && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
