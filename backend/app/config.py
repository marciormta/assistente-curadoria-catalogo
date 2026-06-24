"""Configuração central da aplicação, carregada de variáveis de ambiente (.env)."""
from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Google Gemini ---
    google_api_key: str = ""
    # Geração da resposta final (qualidade > custo, mas ainda barato)
    gen_model: str = "gemini-2.5-flash"
    # Roteamento/classificação + extração de filtros (tarefa simples => modelo mais barato)
    router_model: str = "gemini-2.5-flash-lite"
    # Embeddings do catálogo
    embedding_model: str = "models/gemini-embedding-001"

    # --- ChromaDB ---
    chroma_dir: str = "./data/chroma"
    collection_name: str = "catalogo_livros"

    # --- Dados ---
    books_path: str = "./data/books.json"

    # --- RAG ---
    top_k: int = 5
    # Score mínimo de relevância (0..1) para considerar que há contexto útil.
    # Abaixo disso, tratamos como "não encontrei no catálogo". Ponto de tuning.
    relevance_threshold: float = 0.25

    # --- LangSmith (observabilidade, opcional, plano free) ---
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "curadoria-catalogo"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # --- App ---
    cors_origins: str = "*"


settings = Settings()


def configurar_langsmith() -> None:
    """Ativa o tracing do LangSmith via variáveis de ambiente, se configurado."""
    import os

    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
