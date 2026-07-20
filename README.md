# Xastrinxop WhatsApp Bot

Flask webhook server that receives WhatsApp messages via Green API and processes orders with LangGraph + OpenAI.

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
cd src && python app.py
```

Requires a running [xastrinxop-api](../xastrinxop-api/) instance.

## Environment variables

See `.env.example` and the workspace root `.env.example`.

## Tests

```bash
cd src
pytest test/ -q
```
