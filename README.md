# Assistente de Curadoria do Catálogo

MVP de um assistente que responde perguntas sobre um catálogo de livros de uma
editora

- **Backend:** Python · FastAPI · LangGraph · LangChain
- **LLM/Embeddings:** Google Gemini
- **Vetores:** ChromaDB (vetores **e** metadados juntos)
- **Observabilidade:** LangSmith
- **Frontend:** HTML + CSS + JS puro
- **Infra:** Docker / docker-compose

---

## 1. Como rodar localmente

### Pré-requisitos
- Uma **API key do Google Gemini**
- **Docker + docker-compose**

### — Docker (recomendado)

```bash


docker compose up --build



### Opção  — Local sem Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# indexe o catálogo
python -m app.ingestion.build_index --reset

# suba a API
uvicorn app.main:app --reload --port 8000
```

---


**Fluxo de uma pergunta:**
1. `router` (Gemini) classifica a intenção (`busca` vs `fora_do_escopo`) e extrai filtros
   estruturados (ano, gênero, público, idioma) com *structured output*.
2. `retrieve` faz **busca semântica** no ChromaDB e aplica filtros (ano/idioma no `where` nativo;
   gênero/público por pós-filtro em Python).
3. `generate` (Gemini) escreve a resposta **ancorada apenas no contexto recuperado** e devolve
   os `ids` dos livros realmente usados → viram as **referências**.

---
