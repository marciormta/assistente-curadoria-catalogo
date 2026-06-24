"""Estado compartilhado entre os nós do grafo LangGraph."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    pergunta: str                       # entrada do usuário
    intencao: str                       # "busca" | "fora_do_escopo" (definido pelo router)
    filtros: Optional[Dict[str, Any]]   # filtros extraídos (ano, gênero, ...)
    candidatos: List[Dict[str, Any]]    # livros recuperados do ChromaDB
    resposta: str                       # texto final
    referencias: List[Dict[str, Any]]   # livros efetivamente usados na resposta
