"""
Scraper de Google News RSS para noticias sobre diputados y proyectos de ley.
Estrategia multi-query: busca por nombre del diputado, por bloque y por tema general.
"""

import feedparser
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import time
import logging

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=AR&ceid=AR:es"


def fetch_articles(apellido: str, nombre: str, bloque: str, bill_name: str, max_articles: int = 8) -> list[dict]:
    """
    Busca artículos con tres estrategias y combina los resultados sin duplicados.
    1. Apellido + tema (mención directa del diputado)
    2. Bloque + tema (cobertura por bancada)
    3. Tema solo (contexto general, últimas 3 noticias)
    """
    seen_urls = set()
    articles = []

    queries = [
        (f'"{apellido}" "{bill_name}"', 4),
        (f'"{_short_bloque(bloque)}" "{bill_name}"', 3),
        (f'"{bill_name}" diputados argentina', 2),
    ]

    for query, limit in queries:
        for article in _fetch_rss(query, limit):
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                articles.append(article)

    logger.info(f"  {apellido} / {bill_name}: {len(articles)} artículo(s) encontrado(s)")
    return articles


def _fetch_rss(query: str, limit: int) -> list[dict]:
    url = GOOGLE_NEWS_RSS.format(query=quote(query))
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:limit]:
            article = {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source": entry.get("source", {}).get("title", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
                "content": "",
            }
            content = _fetch_article_content(article["url"])
            if content:
                article["content"] = content[:3000]
            articles.append(article)
            time.sleep(0.3)
        return articles
    except Exception as e:
        logger.warning(f"Error RSS '{query}': {e}")
        return []


def _fetch_article_content(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; QuorumBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        return " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
    except Exception:
        return ""


def _short_bloque(bloque: str) -> str:
    """Versión corta del nombre del bloque para búsquedas más efectivas."""
    shorts = {
        "PROVINCIAS UNIDAS": "Provincias Unidas",
        "INNOVACIÓN FEDERAL": "Innovación Federal",
        "UCR - UNIÓN CÍVICA RADICAL": "UCR",
        "ELIJO CATAMARCA": "Elijo Catamarca",
        "INDEPENDENCIA": "Independencia",
        "COALICIÓN CÍVICA": "Coalición Cívica",
        "ENCUENTRO FEDERAL": "Encuentro Federal",
        "MID": "MID",
        "PARTIDO OBRERO - FIT UNIDAD": "Partido Obrero",
        "PRODUCCIÓN Y TRABAJO": "Producción y Trabajo",
        "PTS - FIT UNIDAD": "PTS izquierda",
        "ADELANTE BUENOS AIRES": "Adelante Buenos Aires",
        "COHERENCIA": "Coherencia",
        "DEFENDAMOS CÓRDOBA": "Defendamos Córdoba",
        "LA NEUQUINIDAD": "La Neuquinidad",
        "POR SANTA CRUZ": "Por Santa Cruz",
        "PRIMERO SAN LUIS": "Primero San Luis",
    }
    return shorts.get(bloque, bloque.title())
