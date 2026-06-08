from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from twilio.twiml.messaging_response import MessagingResponse
from pydantic import BaseModel

from app.language_detect import detect_language_and_register
from app.session import get_session, update_session
from app.llm import generate_response
from app.rag import load_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_knowledge_base()
    yield


app = FastAPI(title="Pana - Venezuela Travel Assistant", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(default=""),
):
    user_phone = From
    message = Body.strip()

    existing_session = get_session(user_phone)
    detection = detect_language_and_register(user_phone, message, existing_session)

    response_text = generate_response(
        user_id=user_phone,
        message=message,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
    )

    update_session(
        user_id=user_phone,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
        message=message,
        response=response_text,
    )

    twilio_response = MessagingResponse()
    twilio_response.message(response_text)
    return Response(content=str(twilio_response), media_type="application/xml")


class ChatMessage(BaseModel):
    message: str
    phone_prefix: str = "+1"


@app.post("/api/chat")
async def web_chat(payload: ChatMessage):
    user_id = f"web_{payload.phone_prefix}"
    message = payload.message.strip()

    existing_session = get_session(user_id)

    fake_phone = payload.phone_prefix + "0000000000"
    detection = detect_language_and_register(fake_phone, message, existing_session)

    response_text = generate_response(
        user_id=user_id,
        message=message,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
    )

    update_session(
        user_id=user_id,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
        message=message,
        response=response_text,
    )

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
