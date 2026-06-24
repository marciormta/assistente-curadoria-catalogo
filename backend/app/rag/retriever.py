"""Camada de recuperação (RAG) sobre o ChromaDB.

Estratégia: busca semântica por embeddings + filtro de metadados.
- Filtros numéricos (ano) e idioma são aplicados direto no ChromaDB (`where`), que é eficiente.
- Filtros "fuzzy" (gênero, público-alvo) são aplicados em Python após a busca, porque `generos`
  é uma lista e o catálogo usa rótulos livres — fazer substring em Python é mais robusto aqui.
  Trade-off documentado no README.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma

from app.config import settings
from app.rag.embeddings import get_embeddings


def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )


def _build_chroma_where(filtros: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Monta o filtro nativo do Chroma para ano e idioma."""
    if not filtros:
        return None
    conds: List[Dict[str, Any]] = []
    if filtros.get("ano_min") is not None:
        conds.append({"ano_publicacao": {"$gte": int(filtros["ano_min"])}})
    if filtros.get("ano_max") is not None:
        conds.append({"ano_publicacao": {"$lte": int(filtros["ano_max"])}})
    if filtros.get("idioma"):
        conds.append({"idioma": {"$eq": filtros["idioma"]}})

    if not conds:
        return None
    if len(conds) == 1:
        return conds[0]
    return {"$and": conds}


def _python_postfilter(itens: List[Dict[str, Any]], filtros: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filtra gênero e público-alvo por substring case-insensitive."""
    if not filtros:
        return itens
    genero = (filtros.get("genero") or "").lower().strip()
    publico = (filtros.get("publico_alvo") or "").lower().strip()
    if not genero and not publico:
        return itens

    out = []
    for it in itens:
        m = it["metadata"]
        if genero and genero not in m.get("generos", "").lower():
            continue
        if publico and publico not in m.get("publico_alvo", "").lower():
            continue
        out.append(it)
    return out


def _tem_filtro_python(filtros: Optional[Dict[str, Any]]) -> bool:
    if not filtros:
        return False
    return bool(filtros.get("genero") or filtros.get("publico_alvo"))


def buscar(query: str, filtros: Optional[Dict[str, Any]] = None, k: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retorna os livros mais relevantes para a query, já com filtros aplicados.

    Cada item: {id, titulo, autores, generos, ano_publicacao, score, sinopse, metadata}
    """
    k = k or settings.top_k
    vs = get_vectorstore()
    where = _build_chroma_where(filtros)

    # Se vamos filtrar em Python depois, recuperamos mais candidatos para não esvaziar o resultado.
    fetch_k = k * 5 if _tem_filtro_python(filtros) else k

    pares = vs.similarity_search_with_relevance_scores(query, k=fetch_k, filter=where)

    itens: List[Dict[str, Any]] = []
    for doc, score in pares:
        m = doc.metadata
        itens.append(
            {
                "id": m.get("id"),
                "titulo": m.get("titulo"),
                "autores": [a.strip() for a in m.get("autores", "").split(";") if a.strip()],
                "generos": [g.strip() for g in m.get("generos", "").split("|") if g.strip()],
                "ano_publicacao": m.get("ano_publicacao"),
                "score": round(float(score), 4),
                "sinopse": m.get("sinopse", ""),
                "metadata": m,
            }
        )

    itens = _python_postfilter(itens, filtros)
    return itens[:k]
