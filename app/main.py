import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from twilio.twiml.messaging_response import MessagingResponse
from pydantic import BaseModel

from app.language_detect import detect_language_and_register
from app.session import get_session, update_session
from app.llm import generate_response
from app.rag import load_knowledge_base, get_destinations, get_destination_by_slug
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_knowledge_base()
    yield


app = FastAPI(title="Pana - Venezuela Travel Assistant", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "pana_verify_2026")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")


def get_base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:8000"))
    return f"{scheme}://{host}"


def process_message(user_id: str, phone_number: str, message: str, base_url: str) -> tuple[str, dict]:
    existing_session = get_session(user_id)
    detection = detect_language_and_register(phone_number, message, existing_session)

    response_text = generate_response(
        user_id=user_id,
        message=message,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
        base_url=base_url,
    )

    update_session(
        user_id=user_id,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
        message=message,
        response=response_text,
    )

    return response_text, detection


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request):
    destinations = get_destinations()
    base_url = get_base_url(request)
    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "destinations": destinations,
        "base_url": base_url,
    })


@app.get("/destination/{slug}", response_class=HTMLResponse)
async def destination_detail(request: Request, slug: str):
    dest = get_destination_by_slug(slug)
    if not dest:
        return HTMLResponse("<h1>Destination not found</h1>", status_code=404)
    base_url = get_base_url(request)
    return templates.TemplateResponse("destination.html", {
        "request": request,
        "dest": dest,
        "base_url": base_url,
    })


# --- Twilio WhatsApp Webhook ---

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(default=""),
):
    user_phone = From
    message = Body.strip()
    base_url = get_base_url(request)

    response_text, _ = process_message(user_phone, user_phone, message, base_url)

    twilio_response = MessagingResponse()
    twilio_response.message(response_text)
    return Response(content=str(twilio_response), media_type="application/xml")


# --- Meta WhatsApp Cloud API Webhook ---

@app.get("/webhook/meta")
async def meta_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@app.post("/webhook/meta")
async def meta_webhook(request: Request):
    body = await request.json()
    base_url = get_base_url(request)

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return JSONResponse({"status": "no messages"})

        msg = messages[0]
        if msg.get("type") != "text":
            return JSONResponse({"status": "non-text message ignored"})

        from_number = msg["from"]
        message_text = msg["text"]["body"].strip()
        user_phone = f"+{from_number}"

        response_text, _ = process_message(user_phone, user_phone, message_text, base_url)

        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {META_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": from_number,
                    "type": "text",
                    "text": {"body": response_text},
                },
            )

    except Exception:
        pass

    return JSONResponse({"status": "ok"})


# --- Web Chat API ---

class ChatMessage(BaseModel):
    message: str
    phone_prefix: str = "+1"


@app.post("/api/chat")
async def web_chat(request: Request, payload: ChatMessage):
    user_id = f"web_{payload.phone_prefix}"
    message = payload.message.strip()
    base_url = get_base_url(request)
    fake_phone = payload.phone_prefix + "0000000000"

    response_text, detection = process_message(user_id, fake_phone, message, base_url)

    return {
        "response": response_text,
        "detected_language": detection["language"],
        "register": detection["register"],
        "origin": detection["origin"],
    }


class ResetRequest(BaseModel):
    phone_prefix: str = "+1"


@app.post("/api/reset")
async def reset_chat(payload: ResetRequest):
    from app.session import clear_session
    user_id = f"web_{payload.phone_prefix}"
    clear_session(user_id)
    return {"status": "session cleared"}
