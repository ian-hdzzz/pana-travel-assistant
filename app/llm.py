import os
import httpx
from groq import Groq
from openai import OpenAI

from app.config import LLM_PROVIDER, OPENAI_API_KEY, GROQ_API_KEY, MODEL_NAME
from app.personality import (
    PANA_SYSTEM_PROMPT,
    REGISTER_INSTRUCTIONS,
    EMERGENCY_OVERRIDE,
)
from app.emergency import check_emergency
from app.rag import search_knowledge
from app.session import get_history

_client = None


def get_client():
    global _client
    if _client is None:
        if LLM_PROVIDER == "groq" and GROQ_API_KEY:
            _client = Groq(api_key=GROQ_API_KEY)
        elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
            _client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            _client = "demo"
    return _client


DEMO_RESPONSES = {
    "venezolano_full": "Epa chamo! Bienvenido pana. Mira, tengo varias opciones brutales para ti dependiendo de lo que busques. Si eres de los que les gusta la aventura heavy, el Pico Bolívar con Uro Adventure es una vaina increíble — 2 días subiendo con guías certificados, campamento en la base histórica de Domingo Peña. Ahora, si quieres algo más relajado pero igual de espectacular, la Cascada 7 Pisos con Cruz de Bolívar es un road trip de 2 días por el oriente con playa, cascada y posada con vista al mar. ¿Qué te llama más la atención?",
    "latam_neutral": "¡Hola! Qué bueno que estás pensando en Venezuela. Mira, tengo varias experiencias increíbles para recomendarte. Desde trekking en los tepuyes (Roraima es una experiencia de otro mundo — 6 días de caminata hasta la cima de una mesa prehistórica), hasta playas espectaculares en el oriente con la Cascada 7 Pisos. ¿Qué tipo de aventura te interesa más? ¿Naturaleza extrema, playa, o algo más cultural en Caracas?",
    "international_en": "Hey there! Welcome — I'm Pana, your Venezuelan travel buddy. So glad you're looking into Venezuela! Let me tell you, this country has some of the most incredible natural wonders you'll ever see. We've got Roraima — a 6-day trek to the top of an ancient flat-topped mountain that inspired 'The Lost World.' Or if you want something less intense, there's a gorgeous 2-day trip along the eastern coast with a 7-tier waterfall, golden beaches, and a posada with ocean views. What's your vibe — hardcore adventure or chill exploration?",
    "international_pt": "Olá! Bem-vindo! Sou o Pana, seu amigo venezuelano. Que bom que está pensando em visitar a Venezuela! Olha, temos paisagens que vão te lembrar um pouco do Brasil — mas com um toque completamente diferente. O Roraima é uma caminhada de 6 dias até o topo de um tepuy que parece outro planeta. Se prefere algo mais tranquilo, temos um roteiro de 2 dias no litoral com cachoeira de 7 andares e praias de areia dourada. O que te interessa mais?",
    "international_fr": "Bonjour ! Bienvenue ! Je suis Pana, votre ami vénézuélien. Ravi que vous vous intéressiez au Venezuela ! Nous avons des paysages absolument extraordinaires — le Roraima est une randonnée de 6 jours jusqu'au sommet d'un tepuy ancien, ou si vous préférez quelque chose de plus détendu, il y a un circuit de 2 jours sur la côte est avec une cascade à 7 niveaux et des plages magnifiques. Qu'est-ce qui vous attire le plus ?",
    "international_de": "Hallo! Willkommen! Ich bin Pana, dein venezolanischer Reisefreund. Schön, dass du dich für Venezuela interessierst! Wir haben unglaubliche Naturwunder — der Roraima ist eine 6-Tage-Wanderung auf einen uralten Tafelberg, der wie eine andere Welt aussieht. Oder wenn du etwas Entspannteres suchst, gibt es einen 2-Tage-Trip an der Ostküste mit einem 7-stufigen Wasserfall und wunderschönen Stränden. Was interessiert dich mehr?",
    "international_it": "Ciao! Benvenuto! Sono Pana, il tuo amico venezuelano. Che bello che stai pensando al Venezuela! Abbiamo paesaggi incredibili — il Roraima è un trekking di 6 giorni fino alla cima di un tepuy antico che sembra un altro pianeta. Oppure se preferisci qualcosa di più rilassato, c'è un viaggio di 2 giorni sulla costa orientale con una cascata a 7 livelli e spiagge meravigliose. Cosa ti attira di più?"
}


def build_system_prompt(message: str, language: str, register: str, origin: str, base_url: str = "") -> tuple[str, bool]:
    is_emergency = check_emergency(message)

    if is_emergency:
        return EMERGENCY_OVERRIDE, True

    rag_context = search_knowledge(message)
    register_instructions = REGISTER_INSTRUCTIONS.get(register, REGISTER_INSTRUCTIONS["latam_neutral"])
    system_prompt = PANA_SYSTEM_PROMPT.format(
        register_instructions=register_instructions,
        language=language,
        register=register,
        origin=origin,
        rag_context=rag_context,
        base_url=base_url,
    )
    return system_prompt, False


def generate_response(
    user_id: str,
    message: str,
    language: str,
    register: str,
    origin: str,
    base_url: str = "",
) -> str:
    client = get_client()

    system_prompt, is_emergency = build_system_prompt(message, language, register, origin, base_url)

    if client == "demo":
        if is_emergency:
            return "EMERGENCY: Please call 171 immediately for ambulance/fire services, or CICPC at 0800-00-24247 for police. If you are in immediate danger, seek shelter and call emergency services. Stay calm. What is your exact location and situation?"
        return DEMO_RESPONSES.get(register, DEMO_RESPONSES["international_en"])

    history = get_history(user_id)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.8,
        max_tokens=400,
    )

    return response.choices[0].message.content
