"""
Análisis de intención de voto usando Gemini Flash.
Dado un conjunto de artículos sobre un diputado y un proyecto,
retorna: intention, confidence, quote, source, reasoning.
"""

import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

INTENTIONS = ["favor", "contra", "abstencion", "sin_info"]

SYSTEM_PROMPT = """Sos un analista político especializado en el Congreso argentino.
Tu tarea es determinar la intención de voto de un diputado/a nacional sobre un proyecto de ley específico,
basándote exclusivamente en las noticias y declaraciones que se te proporcionan.

Reglas:
- Si el diputado no se pronunció o no hay información clara → "sin_info"
- Si hay señales de apoyo (votará a favor, apoya, acompaña, respalda) → "favor"
- Si hay señales de rechazo (votará en contra, rechaza, se opone) → "contra"
- Si hay señales de abstención o dudas explícitas → "abstencion"
- confidence: número entre 0.0 y 1.0 (qué tan segura es la clasificación)
- quote: cita textual del artículo más relevante (máx 150 caracteres), o null si no hay
- source: nombre del medio de la cita, o null
- reasoning: explicación breve de tu análisis (1-2 oraciones)

Respondé ÚNICAMENTE con JSON válido, sin markdown ni explicaciones adicionales."""


def analyze_deputy_intent(
    apellido: str,
    nombre: str,
    bloque: str,
    bill_name: str,
    articles: list[dict],
) -> dict:
    if not articles:
        return _no_info_result()

    articles_text = _format_articles(articles)

    user_prompt = f"""Diputado/a: {nombre} {apellido} (bloque: {bloque})
Proyecto de ley: {bill_name}

Artículos encontrados:
{articles_text}

Determiná la intención de voto. Respondé con JSON:
{{
  "intention": "favor" | "contra" | "abstencion" | "sin_info",
  "confidence": 0.0-1.0,
  "quote": "...",
  "source": "...",
  "reasoning": "..."
}}"""

    try:
        model = _get_model()
        response = model.generate_content(
            user_prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 512},
        )
        raw = response.text.strip()
        # Limpiar posible markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)

        if result.get("intention") not in INTENTIONS:
            result["intention"] = "sin_info"
        result["confidence"] = float(result.get("confidence", 0.0))
        return result

    except Exception as e:
        logger.warning(f"Error Gemini para {apellido}: {e}")
        return _no_info_result()


def _get_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada")
    genai.configure(api_key=api_key)

    # Auto-descubrir modelo disponible (igual que en el bot existente)
    for m in genai.list_models():
        if "gemini-1.5-flash" in m.name and "generateContent" in m.supported_generation_methods:
            return genai.GenerativeModel(
                model_name=m.name,
                system_instruction=SYSTEM_PROMPT,
            )
    # Fallback
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


def _format_articles(articles: list[dict]) -> str:
    parts = []
    for i, a in enumerate(articles, 1):
        content = a.get("content") or a.get("summary", "")
        parts.append(
            f"[Artículo {i}] Fuente: {a.get('source', 'Desconocida')}\n"
            f"Título: {a.get('title', '')}\n"
            f"Texto: {content[:1500]}"
        )
    return "\n\n".join(parts)


def _no_info_result() -> dict:
    return {
        "intention": "sin_info",
        "confidence": 0.0,
        "quote": None,
        "source": None,
        "reasoning": "No se encontraron artículos relevantes.",
    }
