"""API FastAPI do Assistente de Curadoria do Catálogo."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import build_graph, responder
from app.config import configurar_langsmith, settings
from app.schemas import AskRequest, AskResponse, BookRef

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("curadoria")

configurar_langsmith()

app = FastAPI(
    title="Assistente de Curadoria do Catálogo",
    description="RAG sobre catálogo de livros, orquestrado com LangGraph + Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Compila o grafo uma vez (warm-up) e avisa se o índice estiver vazio.
    build_graph()
    try:
        from app.rag.retriever import get_vectorstore

        n = get_vectorstore()._collection.count()  # noqa: SLF001
        if n == 0:
            logger.warning("Índice vazio! Rode: python -m app.ingestion.build_index --reset")
        else:
            logger.info("Índice carregado com %d livros.", n)
    except Exception as e:  # pragma: no cover
        logger.warning("Não foi possível checar o índice: %s", e)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "modelo_geracao": settings.gen_model}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        estado = responder(req.pergunta)
    except Exception as e:  # pragma: no cover
        logger.exception("Erro ao processar pergunta")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

    referencias = [
        BookRef(
            id=r["id"],
            titulo=r["titulo"],
            autores=r.get("autores", []),
            generos=r.get("generos", []),
            ano_publicacao=r.get("ano_publicacao"),
            score=r.get("score"),
        )
        for r in estado.get("referencias", [])
    ]

    return AskResponse(
        resposta=estado.get("resposta", ""),
        referencias=referencias,
        intencao=estado.get("intencao", "busca"),
        filtros=estado.get("filtros"),
    )
