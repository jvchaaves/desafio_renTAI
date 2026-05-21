# ADR-005 — Separação treino/inferência via artifact de centroides

## Problema

A primeira versão do `Orchestrator` chamava `_try_fit_from_dataset`
quando a primeira requisição chegava em `/v1/validate`. Para responder
um único PDF, o servidor lia `labels.csv`, rodava OCR nos 41 documentos
rotulados, carregava sentence-transformers, computava embeddings e só
depois calculava os centroides. O cliente ficava esperando mais de 5
minutos.

O problema não era só o tempo: o servidor passou a depender de
`data/labeled/` existir e estar correto em runtime. em ML descobri que 
treino e inferência são fases distintas  o servidor de inferência
deveria carregar artifacts pré-computados, não refazer o treino a cada
boot.

## Decisão

A solução foi quebrar isso em duas fases.

Em fase offline, um script (`src/app/training/build_artifact.py`) lê
o `labels.csv` junto com o cache de extração e salva os centroides
positivo e negativo em `artifacts/centroids.npz`. Junto vai um
`centroids.meta.json` registrando o modelo de embeddings usado, a
dimensão, o número de exemplos por classe, o hash SHA-256 do
`labels.csv` daquele build e a data  informação suficiente para
auditar qual versão dos centroides está rodando em produção.

Em runtime, o orchestrator carrega o artifact no startup do FastAPI
via `_load_centroids_artifact()`. Não há OCR no boot, e a inferência
não depende mais de `data/`. O lifespan do FastAPI chama
`get_orchestrator()` para forçar o pre carregamento dos modelos e do artifact
antes da primeira request chegar.

## Fluxo resultante

```
Offline (manual ou CI):
  PYTHONPATH=src python -m app.evaluation.runner extract  # popula cache/extracted/
  PYTHONPATH=src python -m app.training.build_artifact    # gera artifacts/centroids.npz
  git add artifacts/  # versiona o artifact com o release

Online (boot do servidor):
  uvicorn app.main:app
    └── lifespan startup
          ├── carrega artifact (~50ms)
          ├── carrega sentence-transformers (~7s primeira vez)
          ├── carrega CLIP (~3s primeira vez)
          └── pronto

Por requisição:
  ~500ms para PDF nativo, ~3-5s para imagem com OCR
```

## Alternativas consideradas

- **Quick fix — fit no startup do FastAPI**: ainda dependeria de
  `data/` em produção e faria OCR no boot. Descartado.
- **Fit lazy na primeira request**: estado atual problemático.
- **Treinar com modelo serializado completo (pickle)**: maior, frágil
  contra mudanças de versão. Centroides como `.npz` são leves (~12KB)
  e portáveis.

## Consequências

Do lado positivo: o startup ficou determinístico e rápido, a
inferência não toca mais `data/`, e o artifact versionado deixa
explícito qual versão dos centroides está em produção (via hash e
metadata). É também o padrão esperado em qualquer projeto de MLOps
maduro.

Do lado negativo: o avaliador precisa rodar `build_artifact` uma vez
antes do primeiro `uvicorn` — está documentado no README. E o artifact
tem que ser regenerado sempre que `labels.csv` muda, senão o hash no
`meta.json` diverge da realidade. Esse último ponto é mais feature
que bug.

