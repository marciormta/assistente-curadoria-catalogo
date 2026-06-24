"""Nós do grafo LangGraph.

Fluxo:
    router ──┬─► retrieve ─► generate ─► END
             └─► fora_do_escopo ─► END
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.agent.state import AgentState
from app.rag.embeddings import get_gen_llm, get_router_llm
from app.rag.prompts import GENERATE_SYSTEM, ROUTER_SYSTEM, montar_contexto
from app.rag.retriever import buscar
from app.config import settings


# --------------------------------------------------------------------------- #
# Schemas de saída estruturada
# --------------------------------------------------------------------------- #
class Filtros(BaseModel):
    genero: Optional[str] = Field(None, description="Gênero citado, se houver.")
    publico_alvo: Optional[str] = Field(None, description="Público-alvo citado, se houver.")
    idioma: Optional[str] = Field(None, description="Idioma citado, ex: pt-BR.")
    ano_min: Optional[int] = Field(None, description="Ano mínimo (inclusive).")
    ano_max: Optional[int] = Field(None, description="Ano máximo (inclusive).")


class RotaDecisao(BaseModel):
    intencao: str = Field(description='"busca" ou "fora_do_escopo".')
    filtros: Filtros = Field(default_factory=Filtros)


class RespostaGerada(BaseModel):
    resposta: str = Field(description="Texto final para o usuário, em pt-BR.")
    ids_utilizados: List[str] = Field(default_factory=list, description="IDs dos livros realmente usados.")


# --------------------------------------------------------------------------- #
# Nós
# --------------------------------------------------------------------------- #
def router_node(state: AgentState) -> AgentState:
    """Classifica a intenção e extrai filtros."""
    llm = get_router_llm().with_structured_output(RotaDecisao)
    decisao: RotaDecisao = llm.invoke(
        [("system", ROUTER_SYSTEM), ("human", state["pergunta"])]
    )

    filtros = {k: v for k, v in decisao.filtros.model_dump().items() if v is not None}
    intencao = decisao.intencao if decisao.intencao in ("busca", "fora_do_escopo") else "busca"

    return {**state, "intencao": intencao, "filtros": filtros or None}


def retrieve_node(state: AgentState) -> AgentState:
    """Busca semântica + filtros no ChromaDB."""
    candidatos = buscar(state["pergunta"], filtros=state.get("filtros"))
    return {**state, "candidatos": candidatos}


def generate_node(state: AgentState) -> AgentState:
    """Gera a resposta ancorada no contexto recuperado."""
    candidatos = state.get("candidatos", [])

    # Guard-rail simples de "não sei": se nada veio ou o melhor score é fraco,
    # ainda mandamos ao LLM, mas o prompt o instrui a admitir que não encontrou.
    melhor_score = max((c.get("score", 0) for c in candidatos), default=0.0)
    contexto_fraco = (not candidatos) or (melhor_score < settings.relevance_threshold)

    contexto = montar_contexto(candidatos)
    aviso = (
        "\n\nATENÇÃO: o contexto abaixo tem baixa relevância para a pergunta. "
        "Se realmente não houver livro adequado, diga que não encontrou no catálogo."
        if contexto_fraco
        else ""
    )

    human = (
        f"Pergunta do usuário:\n{state['pergunta']}\n\n"
        f"CONTEXTO (livros recuperados do catálogo):{aviso}\n\n{contexto}"
    )

    llm = get_gen_llm().with_structured_output(RespostaGerada)
    saida: RespostaGerada = llm.invoke([("system", GENERATE_SYSTEM), ("human", human)])

    usados = set(saida.ids_utilizados or [])
    referencias = [c for c in candidatos if c["id"] in usados]
    # Fallback: se o LLM respondeu mas não marcou ids, usamos os candidatos como referência.
    if not referencias and not contexto_fraco and saida.resposta:
        referencias = candidatos

    return {**state, "resposta": saida.resposta, "referencias": referencias}


def fora_do_escopo_node(state: AgentState) -> AgentState:
    """Resposta curta para saudações / perguntas meta, sem chamar o RAG."""
    msg = (
        "Olá! Sou o Assistente de Curadoria do Catálogo. Posso responder perguntas sobre os livros "
        "da editora: sinopses, recomendações, livros parecidos, listas por tema, gênero ou público, "
        "e filtros como ano de publicação. O que você gostaria de saber sobre o catálogo?"
    )
    return {**state, "resposta": msg, "referencias": []}


# --------------------------------------------------------------------------- #
# Função de roteamento condicional
# --------------------------------------------------------------------------- #
def decidir_rota(state: AgentState) -> str:
    return "fora_do_escopo" if state.get("intencao") == "fora_do_escopo" else "busca"
