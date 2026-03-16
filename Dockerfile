FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install pillow

EXPOSE 5555

CMD ["python", "server.py"]