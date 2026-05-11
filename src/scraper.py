"""
Scraper de Google News RSS para noticias sobre diputados y proyectos de ley.
No requiere API key. Usa el feed público de Google News Argentina.
"""

import feedparser
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import time
import logging

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=AR&ceid=AR:es"

SOURCES_KEYWORDS = [
    "infobae", "lanacion", "clarin", "pagina12", "cronista",
    "ambito", "perfil", "telam", "minutouno", "diarioar",
    "parlamentario", "laizquierdadiario"
]


def build_query(apellido: str, nombre: str, bill_name: str) -> str:
    first_name = nombre.split()[0]
    return f'"{apellido}" "{first_name}" "{bill_name}"'


def fetch_articles(apellido: str, nombre: str, bill_name: str, max_articles: int = 5) -> list[dict]:
    query = build_query(apellido, nombre, bill_name)
    url = GOOGLE_NEWS_RSS.format(query=quote(query))

    try:
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:max_articles]:
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
            time.sleep(0.5)

        logger.info(f"  {apellido} / {bill_name}: {len(articles)} artículo(s) encontrado(s)")
        return articles

    except Exception as e:
        logger.warning(f"Error scraping {apellido}: {e}")
        return []


def _fetch_article_content(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; QuorumBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Eliminar scripts, estilos y nav
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        paragraphs = soup.find_all("p")
        return " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
    except Exception:
        return ""
