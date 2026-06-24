"""Indexação do catálogo: books.json -> embeddings -> ChromaDB.

Uso:
    python -m app.ingestion.build_index           # indexa se a coleção estiver vazia
    python -m app.ingestion.build_index --reset   # apaga e reindexa do zero

Cada livro vira UM documento. O texto embeddado concatena título, autores, gêneros,
público-alvo e sinopse (os campos com sinal semântico). Os metadados ficam guardados
no Chroma para permitir filtros (ano, idioma, gênero, público).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from langchain_core.documents import Document

from app.config import settings
from app.rag.retriever import get_vectorstore


def _carregar_livros(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, list):
        raise ValueError("books.json deve ser uma lista de livros.")
    return dados


def _texto_para_embedding(livro: Dict[str, Any]) -> str:
    autores = ", ".join(livro.get("autores", []))
    generos = ", ".join(livro.get("generos", []))
    return (
        f"Título: {livro.get('titulo', '')}\n"
        f"Autores: {autores}\n"
        f"Gêneros: {generos}\n"
        f"Público-alvo: {livro.get('publico_alvo', '')}\n"
        f"Sinopse: {livro.get('sinopse', '')}"
    )


def _metadados(livro: Dict[str, Any]) -> Dict[str, Any]:
    # Chroma só aceita metadados escalares -> listas viram strings.
    return {
        "id": livro.get("id"),
        "titulo": livro.get("titulo"),
        "autores": "; ".join(livro.get("autores", [])),
        "generos": "|".join(livro.get("generos", [])),
        "publico_alvo": livro.get("publico_alvo", ""),
        "ano_publicacao": int(livro["ano_publicacao"]) if livro.get("ano_publicacao") is not None else None,
        "idioma": livro.get("idioma", ""),
        "isbn": str(livro.get("isbn", "")),
        "sinopse": livro.get("sinopse", ""),
    }


def construir_documentos(livros: List[Dict[str, Any]]) -> List[Document]:
    docs = []
    for livro in livros:
        meta = {k: v for k, v in _metadados(livro).items() if v is not None}
        docs.append(Document(page_content=_texto_para_embedding(livro), metadata=meta))
    return docs


def indexar(reset: bool = False) -> int:
    vs = get_vectorstore()

    try:
        n_atual = vs._collection.count()  # noqa: SLF001 (acesso interno aceitável aqui)
    except Exception:
        n_atual = 0

    if n_atual > 0 and not reset:
        print(f"[index] Coleção '{settings.collection_name}' já tem {n_atual} itens. "
              f"Use --reset para reindexar. Pulando.")
        return n_atual

    if reset and n_atual > 0:
        print(f"[index] Resetando coleção '{settings.collection_name}' ({n_atual} itens)...")
        vs.delete_collection()
        vs = get_vectorstore()

    livros = _carregar_livros(settings.books_path)
    docs = construir_documentos(livros)
    ids = [d.metadata["id"] for d in docs]

    print(f"[index] Indexando {len(docs)} livros de {settings.books_path} ...")
    vs.add_documents(docs, ids=ids)
    print(f"[index] OK. Coleção '{settings.collection_name}' persistida em {settings.chroma_dir}.")
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa o catálogo no ChromaDB.")
    parser.add_argument("--reset", action="store_true", help="Apaga e reindexa do zero.")
    args = parser.parse_args()

    if not settings.google_api_key:
        print("[index] ERRO: GOOGLE_API_KEY não configurada (.env). Abortando.", file=sys.stderr)
        sys.exit(1)

    indexar(reset=args.reset)


if __name__ == "__main__":
    main()
