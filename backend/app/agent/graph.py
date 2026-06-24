"""Montagem do grafo LangGraph (o 'orquestrador')."""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    decidir_rota,
    fora_do_escopo_node,
    generate_node,
    retrieve_node,
    router_node,
)
from app.agent.state import AgentState


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("router", router_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("fora_do_escopo", fora_do_escopo_node)

    g.set_entry_point("router")
    g.add_conditional_edges(
        "router",
        decidir_rota,
        {"busca": "retrieve", "fora_do_escopo": "fora_do_escopo"},
    )
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    g.add_edge("fora_do_escopo", END)

    return g.compile()


def responder(pergunta: str) -> AgentState:
    """Atalho síncrono usado pela API e pela avaliação."""
    grafo = build_graph()
    estado_final = grafo.invoke({"pergunta": pergunta})
    return estado_final
