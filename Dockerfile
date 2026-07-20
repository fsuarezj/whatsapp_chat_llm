FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY passenger_wsgi.py ./

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/src
EXPOSE 3000

CMD ["python", "app.py"]
