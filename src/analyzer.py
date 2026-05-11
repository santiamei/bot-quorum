"""
Análisis de intención de voto usando Gemini Flash.
"""

import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

INTENTIONS = ["favor", "contra", "abstencion", "sin_info"]

SYSTEM_PROMPT = """Sos un analista político especializado en el Congreso argentino.
Tu tarea es determinar la intención de voto de un diputado/a nacional sobre un tema o proyecto de ley,
basándote en las noticias y declaraciones proporcionadas.

Criterios de clasificación:
- "favor": hay señales de que el diputado/a votará a favor, apoya, acompaña o respalda el proyecto.
  También se infiere si su bloque declaró apoyo y no hay señales individuales en contrario.
- "contra": hay señales de rechazo, oposición o voto negativo.
  También se infiere si su bloque declaró rechazo y no hay señales individuales en contrario.
- "abstencion": hay señales explícitas de abstención o de estar en duda/indeciso.
- "sin_info": no hay ninguna información útil ni individual ni del bloque. Usá esto como ÚLTIMO recurso.

Importante: los medios suelen mencionar posiciones por bloque, no por diputado individualmente.
Si encontrás la posición del bloque del diputado, usala para inferir su voto (los diputados
generalmente votan con su bloque). Indicá esto en el reasoning.

- confidence: número entre 0.0 y 1.0
  - 0.8-1.0: declaración directa del diputado/a
  - 0.5-0.7: posición clara del bloque
  - 0.3-0.5: inferencia débil o señales mixtas
  - 0.0-0.2: prácticamente sin información
- quote: cita textual más relevante (máx 150 caracteres), o null
- source: nombre del medio de la cita, o null
- reasoning: explicación breve (1-2 oraciones), aclarando si es posición individual o del bloque

Respondé ÚNICAMENTE con JSON válido, sin markdown ni texto adicional."""


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

    user_prompt = f"""Diputado/a: {nombre} {apellido}
Bloque: {bloque}
Tema/Proyecto: {bill_name}

Artículos encontrados:
{articles_text}

Determiná la intención de voto. Si no encontrás información directa sobre este diputado,
buscá la posición de su bloque ({bloque}) e inferí desde ahí.

Respondé con JSON:
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

    for m in genai.list_models():
        if "gemini-1.5-flash" in m.name and "generateContent" in m.supported_generation_methods:
            return genai.GenerativeModel(
                model_name=m.name,
                system_instruction=SYSTEM_PROMPT,
            )
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
