# ADR-002 — Arquitetura multimodal em 3 configurações

## Contexto

Documentos chegam em dois formatos (PDF nativo, PDF escaneado,
imagem).

## Decisão

Implementar e comparar  3 configurações:

| Config | O que usa |
|---|---|
| A | só CLIP (imagem da primeira página) |
| B | só texto (`pypdf` ou PaddleOCR → embeddings → distância de centroide) |
| C | fusão A + B com pesos modulados por `extraction_quality` |

A configuração final de produção é escolhida pelo resultado empírico do
E-001, não definida antes.

## Componentes

**Extração**:
- PDFs nativos: `pypdf` 
- PDFs escaneados e imagens: `PaddleOCR` 
- Fallback: se `pypdf` retorna < 50 chars, vai para OCR

**Embeddings**: `paraphrase-multilingual-mpnet-base-v2`, 768 dim, forte
em portugues.

**CLIP**: ViT-B/32. Prompts positivos descrevem documentos médicos;
negativos descrevem selfies, screenshots, contratos, etc.

**Fusão**:
- `extraction_quality > 0.7`: w_texto = 0.7, w_visual = 0.3
- `0.3 ≤ quality ≤ 0.7`: 0.5 / 0.5
- `quality < 0.3`: w_texto = 0.2, w_visual = 0.8

Justificativa: quando o OCR falhou (texto ruidoso), a visão precisa
dominar. Quando o texto é confiável, ele dita.

## Consequências

Comparar A vs B vs C empiricamente ajuda a entrar em mais casos pois, CLIP defende contra documento visualmente errado em
formato certo com uma demora maior em tempo para isso.
