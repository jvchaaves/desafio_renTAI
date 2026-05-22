# Desafio P04 — Validação de Documentos Clínicos por IA

Entrega do desafio técnico **P04 — Pesquisador(a) em IA**.

## 1. Abordagem

Serviço FastAPI que recebe PDF ou imagem e retorna se é um documento
clínico válido, com score, label, justificativa, limiar aplicado e
motivo da decisão.

Arquitetura **multimodal**, comparada em três configurações:

| Config | Componentes |
|---|---|
| A | só CLIP (sinal visual zero-shot) |
| B | só texto (pypdf/PaddleOCR → embeddings → distância de centroide com LOO CV) |
| C | fusão A + B com pesos modulados por `extraction_quality` |

A configuração de produção (C, vencedora) foi escolhida pelo resultado
empírico do E-001. Justificativa de cada decisão está nos ADRs em
`docs/02-decisoes/`.

### Pipeline

```
arquivo → DocumentRouter → Extractor (pypdf ou PaddleOCR pt-br)
                           ├─→ texto → embeddings → distância de centroide
                           └─→ imagem 1ª página → CLIP zero-shot
                                       ↓
                            ScoreFusion (pesos por extraction_quality)
                                       ↓
                            ThresholdPolicy (base ± ajuste por especialidade)
                                       ↓
                            decisão + justificativa
```

### Fusão multimodal — pesos por qualidade da extração

A fusão é uma média ponderada cujos pesos variam conforme a qualidade
do texto extraído. Quanto pior o OCR / mais escasso o texto nativo,
mais a decisão depende do sinal visual (CLIP).

```
extraction_quality ∈ [0, 1]
       │
       ▼
   ┌───────────────────┬──────────────┬──────────────┐
   │  baixa (<0.30)    │  média       │  alta (>0.70)│
   │  OCR ruim ou      │  intermediária│ PDF nativo  │
   │  texto vazio      │              │ ou OCR limpo │
   ├───────────────────┼──────────────┼──────────────┤
   │  w_texto  = 0.20  │ w_texto=0.50 │ w_texto=0.70 │
   │  w_visual = 0.80  │ w_visual=0.50│ w_visual=0.30│
   └───────────────────┴──────────────┴──────────────┘
       │                     │                │
       ▼                     ▼                ▼
   CLIP domina         pesos iguais     Texto domina
   (foto borrada,      (scan razoável,  (PDF limpo,
   manuscrito)         OCR parcial)     texto rico)
```

Em todos os casos, a fusão é `score = w_texto · t + w_visual · v`. A
justificativa retornada pela API expõe os pesos efetivamente aplicados
(campo `sub_signals.fusion_weights`).

## 2. Como executar

### Pré-requisitos
- Python 3.11+
- Poppler (`brew install poppler` no macOS)
- `uv` (`pip install uv`)

### Instalação
```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e '.[ml,ocr,dev]'
```

### Pré-requisito do serviço — artifact de centroides

O serviço carrega centroides pré-computados de `artifacts/centroids.npz`
no startup (ADR-005, separação treino/inferência). Se você acabou de
clonar o repo, gere o artifact primeiro:

```bash
# 1) Popula cache de extração (carrega PaddleOCR; ~3-5 min)
PYTHONPATH=src python -m app.evaluation.runner extract

# 2) Gera artifacts/centroids.npz a partir do cache (~10s)
PYTHONPATH=src python -m app.training.build_artifact
```

O artifact é versionado neste repo — em geral você só precisa regenerar
quando `data/labeled/labels.csv` muda.

### Subir o serviço
```bash
PYTHONPATH=src uvicorn app.main:app --reload
# Swagger em http://localhost:8000/docs
```

### Testar
```bash
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/config | jq

curl -X POST http://localhost:8000/v1/validate \
  -F "file=@data/raw/clinical/cfm_atestado_PREENCHIDO.pdf" \
  -F "specialty=cardiologia"
```

### Reproduzir o E-001
```bash
PYTHONPATH=src python -m app.evaluation.runner extract
PYTHONPATH=src python -m app.evaluation.runner classify
PYTHONPATH=src python -m app.evaluation.report
```

> Duas fases para evitar OOM ao carregar PaddleOCR + sentence-transformers
> + CLIP no mesmo processo.

## 3. Dataset (41 docs)

| Categoria | Qtd |
|---|---|
| Clínicos válidos | 19 |
| Não-clínicos | 10 |
| Ambíguos / borda | 12 |

Por modo: 28 digital, 9 photo, 4 scan. Composição por `data_strategy`
em `data/labeled/labels.csv`. Scripts reprodutíveis em
`scripts/data_prep/`. Limitações em
`docs/07-confianca/limitacoes-do-dataset.md`.

Os 41 docs distribuem-se em 26 grupos de origem (templates). 6 grupos
têm múltiplas variações — usados para validação Leave-One-Group-Out
(ver ADR-004).

### Schema do `labels.csv`

| Coluna | Descrição |
|---|---|
| `file_id` | hash SHA-256 truncado |
| `filename` | caminho dentro de `data/raw/` |
| `label` | `clinical` \| `non-clinical` \| `ambiguous` |
| `expected_decision` | `valid` \| `invalid` |
| `doc_type`, `mode`, `specialty` | metadados |
| `data_strategy` | `real` \| `template-fill` \| `template-blank` \| `self-generated` \| `fake-scan` |
| `source`, `license`, `notes` | proveniência |

## 4. Resultados (E-006, validação Leave-One-Group-Out)

| Config | Threshold | Accuracy | Precision | Recall | F1 (pos) | F1 macro |
|---|---|---|---|---|---|---|
| A — só CLIP | uniforme/adaptativo | 0.732 | 0.676 | 1.000 | 0.807 | 0.683 |
| B — só texto | uniforme | 0.561 | 0.600 | 0.652 | 0.625 | 0.548 |
| B — só texto | adaptativo | 0.634 | 0.643 | 0.783 | 0.706 | 0.611 |
| C — fusão | uniforme | 0.780 | 0.733 | 0.957 | 0.830 | 0.760 |
| **C — fusão** | **adaptativo** | **0.805** | **0.742** | **1.000** | **0.852** | **0.783** |

**Configuração vencedora: C com threshold adaptativo.**

Matriz de confusão (Config C adaptive, n=41):

|   | predito VALID | predito invalid |
|---|---|---|
| expected valid (23) | TP=23 | **FN=0** |
| expected invalid (18) | FP=8 | TN=10 |

Intervalos de confiança Wilson 95%:

| Métrica | Pontual | CI 95% |
|---|---|---|
| Recall | 1.000 | **[0.857, 1.000]** |
| Precision | 0.742 | [0.568, 0.863] |
| Accuracy | 0.805 | [0.660, 0.898] |

**Interpretação**: recall 1.0 em N=23 positivos significa "0 FN
nesta amostra", não "100% em produção". CI Wilson indica que o recall
verdadeiro pode ser tão baixo quanto 86% em distribuição real. Ver
seção 5.3 e `docs/07-confianca/limitacoes-do-dataset.md`.

### Antes e depois (E-001 → E-006)

| Métrica (Config C adaptive) | E-001 baseline | E-006 final | Δ |
|---|---|---|---|
| Accuracy | 0.625 | 0.805 | +0.180 |
| Precision | 0.667 | 0.742 | +0.075 |
| Recall | 0.286 | 1.000 | +0.714 |
| F1 (pos) | 0.400 | 0.852 | +0.452 |
| F1 macro | 0.564 | **0.783** | **+0.219** |
| TP / FN | 4 / 10 | 23 / 0 | — |

Mudanças que produziram o ganho:

1. Dataset expandido (32 → 41 docs) com variações por template
2. CLIP ViT-B/32 → **ViT-L/14** com prompts portugues
3. Score textual: fórmula linear → **sigmoid com temperatura T=10**
4. Threshold base: 0.70 → **0.50** (ponto teórico de equilíbrio do sigmoid)
5. Validação: LOO → **LOGO** (elimina leakage por template — ADR-004)

### Critério pré-registrado E-003 (limiar adaptativo)

| Config | F1 macro uniforme | F1 macro adaptativo | Δ |
|---|---|---|---|
| A | 0.683 | 0.683 | +0.000 |
| B | 0.548 | 0.611 | +0.063 |
| C | 0.760 | **0.783** | **+0.023** |

ΔF1 > 0.02 em C: critério pré-registrado no ADR-003 confirmado, com
margem menor do que no E-001 baseline (esperado, dado que o threshold
0.50 já cobre melhor a distribuição).

### LOO vs LOGO — diagnóstico de leakage

Mesma configuração final (sigmoid + threshold 0.50), só mudando a
estratégia de cross-validation:

| Config | F1 LOO | F1 LOGO | Δ |
|---|---|---|---|
| A (só CLIP) | 0.683 | 0.683 | 0.000 |
| B (só texto) uniform | 0.696 | **0.548** | **−0.149** |
| C (fusão) adaptive | 0.783 | 0.783 | 0.000 |

B caiu 0.149 sob LOGO — prova empírica de que o classificador textual
estava se beneficiando de ver irmãos do mesmo template no treino.
C não cai porque CLIP é zero-shot. Detalhes em `docs/02-decisoes/ADR-004-validacao-LOGO.md`.

## 5. Análise dos erros (Config C adaptativo, LOGO)

### Falsos positivos (8)

| Arquivo | Score | Categoria | Causa provável |
|---|---|---|---|
| `synthetic_embalagem_remedio.png` | 0.849 | ambiguous | Caixa de remédio com layout estruturado vira "documento" para CLIP |
| `synthetic_curva_febre.png` | 0.840 | ambiguous | Auto-relato manuscrito sem emissor profissional |
| `synthetic_print_portal_sus.png` | 0.837 | ambiguous | Tela do aplicativo SUS — conteúdo de saúde mas não-documento |
| `scielo_hemograma.pdf` | 0.782 | ambiguous | Artigo científico SOBRE hemograma — fala de medicina, não é exame |
| `cfm_atestado_com_marca_amostra.pdf` | 0.767 | ambiguous | Template oficial com marca "AMOSTRA" — não tem paciente real |
| `saude_direta_manual_prescricao.pdf` | 0.666 | ambiguous | Manual educacional para profissionais — não é exame de paciente |
| `scielo_laudo_radiologico.pdf` | 0.633 | ambiguous | Artigo científico SOBRE laudos radiológicos |
| `cfm_atestado_em_branco.pdf` | 0.570 | ambiguous | Template não preenchido — sem paciente |

**Padrão**: todos os 8 FPs estão marcados como `ambiguous` no dataset —
são casos de borda onde nosso critério estrutural rejeita (C2: paciente
identificável; C3: emissor profissional reconhecível), mas o conteúdo
"parece" clínico. O modelo está reconhecendo corretamente o sinal de
saúde; o limite da tarefa é a definição operacional, não a capacidade
do modelo.

### Falsos negativos (0)

**Zero FN nesta amostra.** Em N=23 positivos, a fusão multimodal sempre
teve sinal suficiente em pelo menos uma das branches (texto ou CLIP).

### 5.3 Ressalva honesta sobre recall 1.0

Recall 1.0 em N=23 NÃO significa "100% em produção":

- **CI Wilson 95% = [0.857, 1.000]**. Recall verdadeiro pode ser tão
  baixo quanto 86%.
- **Multimodalidade segura**: para FN aparecer, texto E visão precisam
  falhar juntos. Em produção, com fontes mais diversas, isso acontecerá.
- **Composição do dataset**: positivos são templates oficiais (CFM, LME
  federal, encaminhamentos SUS) ou exames com sinal forte. Falta
  "positivos difíceis" (receita rasurada, exame de hospital sem timbre,
  foto de papel amassado).

Estimativa honesta para distribuição real: recall **0.80–0.90**, F1
macro **0.65–0.75**. Ver `docs/07-confianca/limitacoes-do-dataset.md`.

## 6. Análise crítica (item 2.5 do edital)

### Tipos que a abordagem classifica melhor

- Não-clínicos visualmente óbvios (selfie, foto casual, print de
  WhatsApp): score muito baixo, rejeição consistente.
- Documentos com layout institucional reconhecível + texto rico
  (artigos SciELO, contratos PDF nativo): classificados corretamente.

### Tipos que classifica pior

- Documentos clínicos sintéticos preenchidos: subscore (FN sistemático).
- Conteúdo semanticamente clínico mas em formato inválido (embalagem,
  curva manuscrita do paciente): aceitos incorretamente.

### Riscos clínicos de FP e FN

- **FP**: especialista recebe documento irrelevante, descarta em
  segundos. Custo baixo (atenção do gargalo).
- **FN**: paciente sem documento no fluxo. Mitigável pelo front
  reenviar, mas pode ser crítico em especialidades de urgência
  (cardiologia, oncologia). Daí o ajuste adaptativo do ADR-003.

### O que mudaria em produção

- Dataset real com 5000+ documentos rotulados por especialistas.
- Fine-tuning de BERTimbau em portugues (ver ADR-001).
- Calibração empírica do score via Platt scaling ou regressão isotônica.
- Calibração empírica dos ajustes por especialidade.
- Feedback loop com clínicos validando erros pós-deploy.
- Anonimização automática de PII antes do classificador.
- Monitoramento de drift e A/B testing entre versões.

## 7. Ferramentas de IA utilizadas

Detalhes em `docs/06-ia/AI_USAGE_LOG.md`. Resumo:

- **Claude Code** para discussão de arquitetura, estrutura dos docs,
  boilerplate da API e revisão de alternativas.
- Decisões substantivas (definição operacional, casos ambíguos,
  bibliotecas, prompts CLIP, valores de ajuste por especialidade,
  interpretação dos resultados) foram revisadas e ajustadas por mim.
- Principais correções feitas após sugestões da IA: API obsoleta do
  PaddleOCR v3, uso excessivo de memória (3 modelos em RAM ao mesmo
  tempo), escopo inicial inflado.

## Estrutura do repositório

| Pasta / arquivo | Conteúdo |
|---|---|
| `src/app/` | código (FastAPI + pipeline multimodal) |
| `data/` | 41 docs rotulados + `labels.csv` |
| `scripts/data_prep/` | geração reprodutível do dataset (3 scripts) |
| `artifacts/` | `centroids.npz` + `meta.json` (treino offline, ADR-005) |
| `docs/01-spec/` | definição operacional + contrato OpenAPI 3.1 |
| `docs/02-decisoes/` | 5 ADRs (pré-treinado, multimodal, limiar, LOGO, artifact) |
| `docs/03-testes/` | casos de borda pré-registrados |
| `docs/04-experimentos/` | experiment log (E-001 baseline + E-006 final) |
| `docs/05-resultados/` | métricas, relatório gerado e snapshots LOO/baseline |
| `docs/06-ia/` | registro de uso de IA |
| `docs/07-confianca/` | limitações do dataset (L1–L7) |
| `pyproject.toml` | dependências (core, `[ml]`, `[ocr]`, `[dev]`) |
| `.env` | configuração local (threshold, pesos, MIME types) podem ser visualizadas em config por não se tratar de algo sigiloso |
