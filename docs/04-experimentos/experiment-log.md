# Experiment log

## Experimentos planejados

| ID | Pergunta | Status |
|---|---|---|
| E-001 | Qual configuração (A/B/C) tem melhor F1 macro? Limiar adaptativo agrega valor? | concluído (baseline) |
| E-002 | Qualidade do OCR (CER/WER) em comparação a gold data | não executado |
| E-003 | Validação do limiar adaptativo por especialidade | parte de E-001 |
| E-004 | Limiar por qualidade de extração | condicional (não disparado) |
| E-005 | Variação de prompts do CLIP | parte de E-006 |
| E-006 | Auditoria do classificador textual e correção de calibração | concluído (versão final) |

## E-001 — comparação A/B/C com LOO

A pergunta de partida era qual configuração entrega o melhor F1 macro
e se o threshold adaptativo por especialidade agrega algum ganho.

Antes de rodar, registrei três hipóteses: a fusão (C) deveria
empatar ou superar o texto sozinho (B), porque agrega informação
independente; CLIP isolado (A) deveria ser preciso em casos
visualmente óbvios como selfie ou print, mas perder em PDFs nativos
com pouco sinal visual; e a diferença entre threshold uniforme e
adaptativo deveria ser pequena em A e B, aparecendo só em C se a
fusão realmente amplificasse o sinal.

Setup: 32 docs do `data/labeled/labels.csv` (composição original,
antes da expansão em E-006), com LOO CV — para cada doc, os
centroides positivo e negativo eram recalculados sobre os 31
restantes.

| Config | Uniforme | Adaptativo | ΔF1 |
|---|---|---|---|
| A (CLIP) | 0.498 | 0.498 | 0.000 |
| B (texto) | 0.360 | 0.360 | 0.000 |
| C (fusão) | 0.459 | **0.564** | **+0.105** |

Vencedor: Config C com threshold adaptativo. As duas primeiras
hipóteses se confirmaram. A terceira também — o ganho do adaptativo só
apareceu em C. Mas B saturou em rejeições com recall zero, o que
soou estranho para um modelo de embeddings que tipicamente separa
classes razoavelmente. Anotei isso para investigar depois (virou
o E-006). Análise dos erros em `docs/05-resultados/relatorio-e001.md`.

## E-003 — limiar adaptativo por especialidade

Critério pré-registrado no ADR-003: se ΔF1 < 0.02, declarar
inconclusivo. Resultado em C foi +0.105, acima do limite. Hipótese
confirmada para configuração multimodal.

## E-006 — auditoria e recalibração (versão final)

E-001 deixou pendurada uma coisa estranha: Config B (texto sozinho)
ficou com F1 0.36 e recall zero — o classificador rejeitava todos os
positivos. Voltei para entender o que estava acontecendo antes de
fechar o projeto com esses números.

Auditando os scores brutos do classificador textual, descobri que o
modelo separava as classes de fato (a similaridade ao centroide
positivo era sistematicamente maior nos clínicos), mas a fórmula que
transformava essa similaridade em score estava apagando o sinal.
A fórmula original era `(sim_pos − sim_neg + 2) / 4`, escrita
assumindo que `sim_pos − sim_neg` poderia variar em [−2, +2]. Na
prática, sentence-embeddings normalizados produzem cossenos quase
sempre em [0.4, 0.9], então essa diferença fica em [−0.3, +0.3].
Resultado: todos os scores ficavam empilhados em [0.44, 0.55], e o
threshold 0.70 inalcançável.

Já que estava mexendo, aproveitei para olhar outras duas coisas que
incomodavam: CLIP estava em ViT-B/32 com prompts só em inglês, o que
desperdiçava capacidade para documentos brasileiros; e o LOO clássico
deixava variações irmãs do mesmo template no treino, o que
provavelmente inflava o F1 do classificador textual.

As mudanças que entraram nesta rodada:

| # | Mudança | Justificativa | Documentado em |
|---|---|---|---|
| 1 | Dataset 32 → 41 docs | mais variações por template | `scripts/data_prep/generate_varied_templates.py` |
| 2 | CLIP ViT-B/32 → ViT-L/14, prompts en+pt | modelo melhor, cobertura pt-br | `src/app/classifiers/visual_clip.py` |
| 3 | Fórmula linear → sigmoid T=10 | corrigir o bug de escala | ADR-003 §Calibração |
| 4 | Threshold base 0.70 → 0.50 | alinhar com ponto de equilíbrio da sigmoid | ADR-003 |
| 5 | LOO → LOGO | eliminar leakage entre variações do mesmo template | ADR-004 |

Comparando o resultado final (Config C com threshold adaptativo,
validação LOGO) contra o baseline E-001:

| Métrica | E-001 baseline | E-006 final | Δ |
|---|---|---|---|
| Accuracy | 0.625 | 0.805 | +0.180 |
| Precision (pos) | 0.667 | 0.742 | +0.075 |
| Recall (pos) | 0.286 | 1.000 | +0.714 |
| F1 (pos) | 0.400 | 0.852 | +0.452 |
| F1 macro | 0.564 | **0.783** | **+0.219** |
| TP / FN | 4 / 10 | 23 / 0 | — |
| FP / TN | 2 / 16 | 8 / 10 | — |

A migração de LOO para LOGO ajudou a separar duas coisas que estavam
misturadas — sinal real vs vazamento de template:

| Config | LOO F1 macro | LOGO F1 macro | Δ |
|---|---|---|---|
| A (CLIP só) | 0.683 | 0.683 | 0 |
| B (texto só) uniform | 0.696 | 0.548 | **−0.149** |
| B (texto só) adaptive | 0.696 | 0.611 | −0.085 |
| C (fusão) adaptive | 0.783 | 0.783 | 0 |

B perde 0.149 quando os irmãos saem do treino — esse era exatamente
o tamanho do ganho artificial que o LOO produzia. C não muda porque
CLIP é zero-shot e não tem o que vazar entre folds. Detalhes em ADR-004.

Intervalos de confiança Wilson 95% para Config C adaptive, N=41:

| Métrica | Pontual | CI 95% |
|---|---|---|
| Recall | 1.000 | [0.857, 1.000] |
| Precision | 0.742 | [0.568, 0.863] |
| Accuracy | 0.805 | [0.660, 0.898] |

Recall 1.0 em 23 positivos está no teto do intervalo — o valor real
em produção provavelmente fica entre 0.86 e 1.00. F1 macro 0.783 é o
número que consigo defender com este dataset e esta validação, e não
deveria ser extrapolado para distribuição real sem novas medições.

## Próximos (não executados)

- E-002 (gold data de OCR): permitiria separar "erro de extração" de
  "erro de classificação". Não foi executado por restrição de tempo.
- E-004: condicional ao fracasso de E-003. Não disparado.
