FROM python:3.13-slim


RUN apt-get update && \
    apt-get install -y wget unzip curl && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN groupadd -r appuser && useradd -r -g appuser -m appuser

WORKDIR /app

COPY . /app

RUN RANDOM_FLAG="$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)" && \
    RANDOM_FILENAME="$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)" && \
    echo "INTIGRITI{$RANDOM_FLAG}" > /flag_$RANDOM_FILENAME.txt && \
    chmod 444 /flag_$RANDOM_FILENAME.txt && \
    echo "Flag copied to /flag_$RANDOM_FILENAME.txt"


RUN mkdir -p /app/instances && \
    chown -R appuser:appuser /app

ENV PATH="/usr/lib/chromium:${PATH}"
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER_BIN="/usr/bin/chromedriver"

EXPOSE 1337

USER appuser

CMD ["python3", "app.py"]
