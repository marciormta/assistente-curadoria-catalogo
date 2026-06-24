#!/bin/sh
set -e

# Indexa o catálogo se a coleção estiver vazia (idempotente).
# Se a GOOGLE_API_KEY não estiver setada, o build_index avisa e aborta — por isso o "|| true",
# para a API ainda subir e o /health responder (a indexação pode ser feita manualmente depois).
echo "[entrypoint] Verificando índice do ChromaDB..."
python -m app.ingestion.build_index || echo "[entrypoint] Indexação pulada/falhou (cheque a GOOGLE_API_KEY). Seguindo."

echo "[entrypoint] Subindo API em 0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
