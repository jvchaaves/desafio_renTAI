# ADR-001 — Pré-treinado open source em vez de treinar do zero

## Contexto

O edital exige um dataset com pelo menos 30 documentos clínicos. Esse
N=41 (versão final) é pequeno demais para fine-tuning robusto ou treino
do zero.

## Decisão

Usar modelos pré-treinados open source, sem treino adicional:

- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` para embeddings textuais
- `open_clip` ViT-B/32 para sinal visual 

Classificação por **distância de centroide** das classes positiva e
negativa, com **leave-one-out cross-validation** na avaliação para evitar
vazamento.

## Alternativas consideradas

- **Treinar do zero**: precisa de milhares de exemplos rotulados. Com
  N=41, overfit garantido.
- **Pré-treinado + LogReg/SVM**: adiciona hiperparâmetros
  (regularização, pesos, kernel). Com N=41, escolher esses valores via
  cross-validation é instável — vira chute disfarçado de método.
- **Pré-treinado + distância de centroide** (escolhida): zero
  hiperparâmetros para tunar. Calcula a média dos embeddings de cada
  classe e compara o documento novo às duas médias. Determinístico,
  robusto a N pequeno, fácil de explicar e auditável.
## Consequências

**Positivas**: metodologia honesta para N pequeno, reprodutibilidade
alta, custo zero de compute.

**Negativas**: performance limitada pela qualidade dos embeddings
pré-treinados. Em produção, com dataset real maior, fine-tuning seria a melhor opção.
