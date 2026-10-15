FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.114.2 uvicorn==0.30.6 docker==7.1.0 httpx==0.28.1 pydantic==2.13.5

COPY . /app

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
