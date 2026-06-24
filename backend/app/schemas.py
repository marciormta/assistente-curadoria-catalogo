"""Modelos de entrada/saída da API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    pergunta: str = Field(..., min_length=1, description="Pergunta em linguagem natural sobre o catálogo.")


class BookRef(BaseModel):
    """Referência a um livro usado na resposta."""
    id: str
    titulo: str
    autores: List[str] = []
    generos: List[str] = []
    ano_publicacao: Optional[int] = None
    score: Optional[float] = None


class AskResponse(BaseModel):
    resposta: str
    referencias: List[BookRef] = []
    intencao: str
    filtros: Optional[Dict[str, Any]] = None
