"""Avaliação da qualidade das respostas.

- Roda todas as perguntas de questions.txt pelo agente.
- Usa LLM-as-judge para classificar cada resposta como: correta | parcial | errada.
- Também reporta métrica de retrieval simples (quantas perguntas tiveram >=1 referência).
- Salva resultado em eval_result.json e imprime uma tabela no terminal.

Uso:
    python -m app.evaluation.run_eval
"""
from __future__ import annotations

import json
import os
from typing import List

from pydantic import BaseModel, Field
from tabulate import tabulate

from app.agent.graph import responder
from app.rag.embeddings import get_gen_llm

AQUI = os.path.dirname(__file__)
QUESTIONS_PATH = os.path.join(AQUI, "questions.txt")
OUT_PATH = os.path.join(AQUI, "eval_result.json")

JUDGE_SYSTEM = """Você é um avaliador rigoroso de um assistente de catálogo de livros.
Receberá: a PERGUNTA do usuário, a RESPOSTA do assistente e as REFERÊNCIAS (livros que ele usou).

Classifique a RESPOSTA em uma das categorias:
- "correta": responde bem à pergunta e é coerente com as referências; sem invenções.
- "parcial": responde em parte, ou é vaga, ou ignora parte do pedido, ou mistura acerto e lacuna.
- "errada": foge do pedido, contradiz as referências, ou inventa informação (alucinação).

Regra importante: se a pergunta pede algo que claramente NÃO existe no catálogo e o assistente
admite honestamente que não encontrou, isso conta como "correta" (recusar-se a alucinar é o certo).

Dê também uma justificativa de 1 frase."""


class Veredito(BaseModel):
    classificacao: str = Field(description='"correta" | "parcial" | "errada"')
    justificativa: str


def carregar_perguntas() -> List[str]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def avaliar() -> None:
    perguntas = carregar_perguntas()
    juiz = get_gen_llm().with_structured_output(Veredito)

    linhas = []
    registros = []
    cont = {"correta": 0, "parcial": 0, "errada": 0}
    com_referencia = 0

    for i, pergunta in enumerate(perguntas, 1):
        estado = responder(pergunta)
        resposta = estado.get("resposta", "")
        refs = estado.get("referencias", [])
        if refs:
            com_referencia += 1

        refs_txt = "; ".join(f"{r['titulo']} ({r['id']})" for r in refs) or "(nenhuma)"
        human = (
            f"PERGUNTA:\n{pergunta}\n\n"
            f"RESPOSTA:\n{resposta}\n\n"
            f"REFERÊNCIAS:\n{refs_txt}"
        )
        veredito: Veredito = juiz.invoke([("system", JUDGE_SYSTEM), ("human", human)])
        cls = veredito.classificacao if veredito.classificacao in cont else "parcial"
        cont[cls] += 1

        linhas.append([i, pergunta[:48], cls, len(refs), veredito.justificativa[:60]])
        registros.append(
            {
                "pergunta": pergunta,
                "resposta": resposta,
                "intencao": estado.get("intencao"),
                "filtros": estado.get("filtros"),
                "referencias": [r["id"] for r in refs],
                "classificacao": cls,
                "justificativa": veredito.justificativa,
            }
        )

    print("\n" + tabulate(linhas, headers=["#", "Pergunta", "Classe", "Refs", "Justificativa"], tablefmt="github"))
    total = len(perguntas)
    print(f"\nResumo: {cont['correta']} corretas | {cont['parcial']} parciais | {cont['errada']} erradas (de {total})")
    print(f"Retrieval: {com_referencia}/{total} perguntas com >=1 referência")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"resumo": cont, "retrieval_com_ref": com_referencia, "total": total, "detalhes": registros},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nResultado salvo em {OUT_PATH}")


if __name__ == "__main__":
    avaliar()
