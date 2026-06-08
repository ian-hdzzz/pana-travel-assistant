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
from app.rag import load_knowledge_base, get_destinations, get_destination_by_slug


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_knowledge_base()
    yield


app = FastAPI(title="Pana - Venezuela Travel Assistant", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:8000"))
    return f"{scheme}://{host}"


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

    existing_session = get_session(user_phone)
    detection = detect_language_and_register(user_phone, message, existing_session)

    response_text = generate_response(
        user_id=user_phone,
        message=message,
        language=detection["language"],
        register=detection["register"],
        origin=detection["origin"],
        base_url=base_url,
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
async def web_chat(request: Request, payload: ChatMessage):
    user_id = f"web_{payload.phone_prefix}"
    message = payload.message.strip()
    base_url = get_base_url(request)

    existing_session = get_session(user_id)

    fake_phone = payload.phone_prefix + "0000000000"
    detection = detect_language_and_register(fake_phone, message, existing_session)

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
