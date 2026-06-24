# Arquitetura

## Visão geral

```mermaid
flowchart TB
    subgraph Cliente
        UI["Frontend<br/>(HTML + CSS + JS)"]
    end

    subgraph API["Backend — FastAPI"]
        EP["POST /ask"]
    end

    subgraph Agente["Orquestrador — LangGraph"]
        R["router<br/>(intenção + filtros)"]
        RET["retrieve<br/>(busca semântica + filtros)"]
        GEN["generate<br/>(resposta ancorada)"]
        FE["fora_do_escopo"]
    end

    DB[("ChromaDB<br/>vetores + metadados")]
    GEM["Google Gemini<br/>embeddings · flash-lite · flash"]

    UI -->|pergunta| EP --> R
    R -->|busca| RET --> GEN --> EP
    R -->|saudação/meta| FE --> EP
    RET <--> DB
    R -.-> GEM
    GEN -.-> GEM
    DB -.->|embeddings| GEM
    EP -->|resposta + referências| UI
```

## Pipeline de ingestão (offline)

```mermaid
flowchart LR
    J["books.json<br/>(~200 livros)"] --> P["1 documento por livro<br/>título+autores+gêneros+sinopse"]
    P --> E["Embeddings<br/>(gemini-embedding-001)"]
    E --> C[("ChromaDB<br/>persistido em disco")]
```

## Decisão central: por que LangGraph com router (e não multi-agente nem SQL)

- **Volume pequeno (~200 livros)** não justifica orquestração multi-agente. Um grafo
  `router → retrieve → generate` entrega a estrutura de orquestrador de forma enxuta e defensável.
- **Filtros** ("infantis após 2015") são resolvidos com **filtro de metadados nativo do ChromaDB**,
  sem precisar de um agente text-to-SQL. SQL só se justificaria com dados relacionais/analíticos
  (ex.: dados de venda, agregações), que não fazem parte deste catálogo.
- O **router** separa "precisa de busca" de "saudação/meta" e extrai filtros estruturados,
  dando um ponto único e observável de decisão.
