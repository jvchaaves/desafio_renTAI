# Relatorio E-001 — Comparacao Config A / B / C

**N = 41** documentos (LOO Cross-Validation para Config B/C).

Gerado automaticamente por `app.evaluation.report`.


## 1. Metricas globais

| Config | Threshold | Accuracy | Precision | Recall | F1 (pos) | F1 macro |
|---|---|---|---|---|---|---|
| **A** | uniform | 0.732 | 0.676 | 1.000 | 0.807 | 0.683 |
| **A** | adaptive | 0.732 | 0.676 | 1.000 | 0.807 | 0.683 |
| **B** | uniform | 0.561 | 0.600 | 0.652 | 0.625 | 0.548 |
| **B** | adaptive | 0.634 | 0.643 | 0.783 | 0.706 | 0.611 |
| **C** | uniform | 0.780 | 0.733 | 0.957 | 0.830 | 0.760 |
| **C** | adaptive | 0.805 | 0.742 | 1.000 | 0.852 | 0.783 |

**Vencedor (F1 macro)**: Config C com threshold adaptive (F1 macro = 0.783).


## 2. Matrizes de confusao (global, threshold uniforme)

| Config | TP | TN | FP | FN |
|---|---|---|---|---|
| **A** | 23 | 7 | 11 | 0 |
| **B** | 15 | 8 | 10 | 8 |
| **C** | 22 | 10 | 8 | 1 |

## 3. Estratificacao por modo (digital / scan / photo)


### Config A (threshold uniforme)

| Modo | N | Accuracy | F1 macro |
|---|---|---|---|
| digital | 30 | 0.733 | 0.627 |
| photo | 8 | 0.625 | 0.564 |
| scan | 3 | 1.000 | 0.500 |

### Config B (threshold uniforme)

| Modo | N | Accuracy | F1 macro |
|---|---|---|---|
| digital | 30 | 0.600 | 0.583 |
| photo | 8 | 0.375 | 0.365 |
| scan | 3 | 0.667 | 0.400 |

### Config C (threshold uniforme)

| Modo | N | Accuracy | F1 macro |
|---|---|---|---|
| digital | 30 | 0.800 | 0.762 |
| photo | 8 | 0.625 | 0.564 |
| scan | 3 | 1.000 | 0.500 |

## 4. Estratificacao por label (clinical / non-clinical / ambiguous)


### Config A (threshold uniforme)

| Label | N | Accuracy | F1 macro |
|---|---|---|---|
| ambiguous | 12 | 0.417 | 0.378 |
| clinical | 19 | 1.000 | 0.500 |
| non-clinical | 10 | 0.600 | 0.375 |

### Config B (threshold uniforme)

| Label | N | Accuracy | F1 macro |
|---|---|---|---|
| ambiguous | 12 | 0.333 | 0.314 |
| clinical | 19 | 0.632 | 0.387 |
| non-clinical | 10 | 0.700 | 0.412 |

### Config C (threshold uniforme)

| Label | N | Accuracy | F1 macro |
|---|---|---|---|
| ambiguous | 12 | 0.333 | 0.250 |
| clinical | 19 | 0.947 | 0.486 |
| non-clinical | 10 | 1.000 | 0.500 |

## 5. Falsos Positivos e Falsos Negativos por configuracao


### Config A

**Falsos positivos (11)** — aceitos mas eram invalidos:

- `non_clinical/agehab_contrato_locacao.pdf` (score=0.8223, label=non-clinical, strategy=real)
- `non_clinical/crecims_contrato_sem_garantia.pdf` (score=0.7897, label=non-clinical, strategy=real)
- `non_clinical/mg_nota_fiscal_modelo1.pdf` (score=0.8992, label=non-clinical, strategy=real)
- `non_clinical/synthetic_rg_anonimo.png` (score=0.5607, label=non-clinical, strategy=self-generated)
- `ambiguous/scielo_laudo_radiologico.pdf` (score=0.8686, label=ambiguous, strategy=real)
- `ambiguous/scielo_hemograma.pdf` (score=0.9907, label=ambiguous, strategy=real)
- `ambiguous/saude_direta_manual_prescricao.pdf` (score=0.9981, label=ambiguous, strategy=real)
- `ambiguous/cfm_atestado_com_marca_amostra.pdf` (score=0.8356, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_embalagem_remedio.png` (score=0.9902, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_curva_febre.png` (score=0.9324, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_print_portal_sus.png` (score=0.9871, label=ambiguous, strategy=self-generated)

**Falsos negativos (0)** — rejeitados mas eram validos:

- nenhum

### Config B

**Falsos positivos (10)** — aceitos mas eram invalidos:

- `non_clinical/synthetic_selfie.jpg` (score=0.5, label=non-clinical, strategy=self-generated)
- `non_clinical/synthetic_food.jpg` (score=0.5, label=non-clinical, strategy=self-generated)
- `non_clinical/synthetic_pet.jpg` (score=0.5, label=non-clinical, strategy=self-generated)
- `ambiguous/scielo_laudo_radiologico.pdf` (score=0.5321, label=ambiguous, strategy=real)
- `ambiguous/scielo_hemograma.pdf` (score=0.6919, label=ambiguous, strategy=real)
- `ambiguous/saude_direta_manual_prescricao.pdf` (score=0.5236, label=ambiguous, strategy=real)
- `ambiguous/cfm_atestado_em_branco.pdf` (score=0.6621, label=ambiguous, strategy=template-blank)
- `ambiguous/cfm_atestado_com_marca_amostra.pdf` (score=0.7369, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_embalagem_remedio.png` (score=0.7074, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_print_portal_sus.png` (score=0.6866, label=ambiguous, strategy=self-generated)

**Falsos negativos (8)** — rejeitados mas eram validos:

- `clinical/synthetic_cartao_vacina.png` (score=0.4612, label=clinical, strategy=self-generated)
- `ambiguous/encaminhamento_se_fake_scan.jpg` (score=0.4724, label=ambiguous, strategy=fake-scan)
- `clinical/encaminhamento_se_v1.pdf` (score=0.4396, label=clinical, strategy=template-fill)
- `clinical/encaminhamento_se_v2.pdf` (score=0.4157, label=clinical, strategy=template-fill)
- `clinical/encaminhamento_se_v3.pdf` (score=0.4531, label=clinical, strategy=template-fill)
- `clinical/goiania_laudo_pericial_v1.pdf` (score=0.4065, label=clinical, strategy=template-fill)
- `clinical/goiania_laudo_pericial_v2.pdf` (score=0.402, label=clinical, strategy=template-fill)
- `clinical/goiania_laudo_pericial_v3.pdf` (score=0.4291, label=clinical, strategy=template-fill)

### Config C

**Falsos positivos (8)** — aceitos mas eram invalidos:

- `ambiguous/scielo_laudo_radiologico.pdf` (score=0.6331, label=ambiguous, strategy=real)
- `ambiguous/scielo_hemograma.pdf` (score=0.7816, label=ambiguous, strategy=real)
- `ambiguous/saude_direta_manual_prescricao.pdf` (score=0.6659, label=ambiguous, strategy=real)
- `ambiguous/cfm_atestado_em_branco.pdf` (score=0.5678, label=ambiguous, strategy=template-blank)
- `ambiguous/cfm_atestado_com_marca_amostra.pdf` (score=0.7665, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_embalagem_remedio.png` (score=0.8488, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_curva_febre.png` (score=0.8397, label=ambiguous, strategy=self-generated)
- `ambiguous/synthetic_print_portal_sus.png` (score=0.8369, label=ambiguous, strategy=self-generated)

**Falsos negativos (1)** — rejeitados mas eram validos:

- `clinical/goiania_laudo_pericial_v1.pdf` (score=0.4967, label=clinical, strategy=template-fill)

## 6. Limiar uniforme vs adaptivo (E-003 pre-registrado)

| Config | F1 macro uniforme | F1 macro adaptivo | Delta |
|---|---|---|---|
| **A** | 0.683 | 0.683 | +0.000 |
| **B** | 0.548 | 0.611 | +0.063 |
| **C** | 0.760 | 0.783 | +0.023 |

*Criterio pre-registrado (ADR-003): se ΔF1 < 0.02 em todas as configs, considerar inconclusivo e migrar para E-004 (limiar por extraction_quality).*
