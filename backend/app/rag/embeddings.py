"""Fábricas de modelos Gemini (embeddings, LLM de geração e LLM de roteamento)."""
from __future__ import annotations

from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Embeddings do catálogo. Reusado tanto na indexação quanto na busca."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


@lru_cache(maxsize=1)
def get_gen_llm() -> ChatGoogleGenerativeAI:
    """LLM que escreve a resposta final. Temperatura baixa => menos alucinação."""
    return ChatGoogleGenerativeAI(
        model=settings.gen_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )


@lru_cache(maxsize=1)
def get_router_llm() -> ChatGoogleGenerativeAI:
    """LLM leve para classificar intenção e extrair filtros. Determinístico."""
    return ChatGoogleGenerativeAI(
        model=settings.router_model,
        google_api_key=settings.google_api_key,
        temperature=0.0,
    )
