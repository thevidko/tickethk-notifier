FROM python:3.13-alpine
WORKDIR /app
COPY check_tickets.py .
ENV PYTHONUNBUFFERED=1 \
    STATE_FILE=/data/state.json \
    INTERVAL=120
VOLUME /data
CMD ["python", "check_tickets.py"]
