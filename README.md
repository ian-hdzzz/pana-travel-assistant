# Pana — Venezuelan AI Travel Assistant

Conversational AI travel assistant with a warm Venezuelan local personality. Supports WhatsApp (Meta Cloud API / Twilio) and web chat.

## Features

- **Local personality**: Pana speaks like a proud Venezuelan friend — uses "chamo", "brutal", "no te lo puedes perder" with locals
- **6-language support**: Spanish, English, Portuguese, French, German, Italian
- **Tone adaptation**: Detects user origin from phone prefix + message content, adjusts register (full slang for Venezuelans, neutral Spanish for Latin Americans, friendly English for internationals)
- **RAG knowledge base**: Semantic search over real destinations/experiences using sentence-transformers + ChromaDB
- **Emergency mode**: Detects emergency keywords across all 6 languages, instantly drops personality and provides emergency numbers
- **Session memory**: Remembers language/register preference per user throughout conversation
- **WhatsApp integration**: Twilio webhook endpoint ready for WhatsApp Business
- **Web chat fallback**: Built-in web UI with origin simulator for testing

## Architecture

```
User (WhatsApp/Web) → FastAPI → Language Detection → Emergency Check
                                      ↓                    ↓
                               Session Manager      Emergency Response
                                      ↓
                               RAG Search (ChromaDB + sentence-transformers)
                                      ↓
                               LLM (Groq/OpenAI) with dynamic system prompt
                                      ↓
                               Response → User
```

## Stack

- **Backend**: FastAPI + Python 3.11
- **LLM**: Groq (Llama 3.1 70B) or OpenAI (GPT-4o) — swappable via config
- **RAG**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
- **WhatsApp**: Twilio / Meta Cloud API
- **Frontend**: Vanilla HTML/CSS/JS web chat

## Quick Start

```bash
# 1. Clone
git clone https://github.com/anirudhatalmale6-alt/pana-travel-assistant.git
cd pana-travel-assistant

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Open http://localhost:8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `groq` or `openai` |
| `GROQ_API_KEY` | If using Groq | Free at console.groq.com |
| `OPENAI_API_KEY` | If using OpenAI | From platform.openai.com |
| `MODEL_NAME` | No | Default: `llama-3.1-70b-versatile` |
| `TWILIO_ACCOUNT_SID` | For WhatsApp | From Twilio console |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | From Twilio console |

## Register System

The bot uses a 3-signal approach to determine tone:

1. **Phone prefix** (+58 = Venezuelan full slang, +57 = neutral LATAM, +1 = English, etc.)
2. **Message analysis** (detects Venezuelan markers like "chamo", "vaina", "chevere")
3. **Explicit override** (user says "habla en inglés" → switches)

Registers: `venezolano_full`, `latam_neutral`, `spanish_formal`, `international_en/pt/fr/de/it`

## WhatsApp Setup (Twilio Sandbox)

1. Get a Twilio account and enable the WhatsApp Sandbox
2. Set webhook URL to `https://your-domain.com/webhook/whatsapp`
3. Send the join code to the sandbox number
4. Start chatting

## Adding Destinations

Edit `knowledge_base/destinations.json` and restart the server. Each destination needs:
- name, location, description, contact, instagram, duration, difficulty, best_for

## Open Source Migration

The architecture supports full open-source deployment:
- LLM: Llama 3.1 70B via Groq (free) or self-hosted via Ollama/vLLM
- Embeddings: all-MiniLM-L6-v2 (already open source)
- Vector DB: ChromaDB (open source)
- No proprietary dependencies required
