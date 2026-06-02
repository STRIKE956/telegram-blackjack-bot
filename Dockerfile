FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py solana_wallet.py storage.py ./
RUN mkdir -p /app/data/wallets

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

CMD ["python", "bot.py"]
