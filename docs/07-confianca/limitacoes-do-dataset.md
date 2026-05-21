# Limitações do dataset

Este documento separa o que foi validado empiricamente do que foi
simulado ou estimado. É usado para interpretar com cautela as métricas
do E-001.

## Composição do dataset (41 docs)

| Estratégia | Qtd | O que significa |
|---|---|---|
| `real` | 8 | Documento publicado sem PII (contratos gov, NF, artigos SciELO) |
| `template-fill` | 15 | Template oficial preenchido com dados sintéticos declarados |
| `template-blank` | 1 | Template oficial não preenchido, caso de borda explícito |
| `self-generated` | 14 | Imagens geradas (PIL/matplotlib) ou CC0 (picsum) |
| `fake-scan` | 3 | PDF nativo renderizado com ruído sintético |

Por modo: 28 digital, 9 photo, 4 scan. A coluna `data_strategy` no
`labels.csv` registra a estratégia de cada arquivo.

## Estrutura por grupos (templates)

26 grupos derivados da raiz do filename. 6 grupos com mais de 1 documento
formam as famílias de templates:

| Grupo | n | Composição |
|---|---|---|
| cfm_atestado | 5 | 3 positivos + 2 ambíguos |
| encaminhamento_se | 4 | 3 positivos + 1 fake_scan |
| lme_federal | 4 | 3 positivos + 1 fake_scan |
| cfm_receituario | 3 | 3 positivos |
| goiania_laudo_pericial | 3 | 3 positivos |
| hematosul_hemograma | 2 | 1 positivo + 1 fake_scan |

Esta estrutura motivou a troca de LOO para LOGO na validação (ADR-004).

## Limitações

### L1 — Templates preenchidos com dados sintéticos

Documentos clínicos válidos preenchidos compartilham layout/header do
template base. Embeddings podem aprender o padrão do template em vez do
que faz algo ser clínico.

**Mitigação aplicada**: variação deliberada (nomes, datas, especialidades
diferentes em cada template) + validação por Leave-One-Group-Out (ADR-004)
que remove todos os irmãos do template ao avaliar cada doc.

**Confirmado empiricamente em E-006**: sob LOGO, Config B (texto sozinho)
cai de F1 0.696 → 0.548 (Δ = −0.149). Esse delta é exatamente o ganho
artificial que LOO produzia ao deixar irmãos do template no treino.
Config C (fusão) não cai porque CLIP é zero-shot e independe do nosso
dataset.

### L2 — Sub-representação de scans de baixa qualidade

A maioria dos PDFs reais coletados são nativos limpos.

**Mitigação**: 3 fake-scans gerados com rotação + blur + JPEG q=55.
Não substituem scans reais, que têm artefatos físicos (sombras,
perspectiva).

### L3 — Sem laudos de imagem clínica em pt-br

Fontes públicas (Open-i NIH, MIMIC-CXR) são em inglês ou exigem
credencial. Incluí 1 laudo sintético de raio-X em inglês como
representante; a definição operacional aceita inglês.

### L4 — N=41 limita validade estatística

Diferenças de F1 menores que ~0.04 estão dentro do ruído. Análise
estratificada por especialidade tem 2-5 docs por estrato — qualitativa,
não conclusiva.

Intervalo de confiança Wilson 95% para recall (23/23) na configuração
final: **[0.857, 1.000]**. O recall verdadeiro em produção pode ser tão
baixo quanto 86%.

### L5 — Curadoria por uma pessoa

Sem revisão independente. Vereditos dos 18 casos-limite refletem minha
leitura. Mitigação: critérios C1-C4 / N1-N7 são explícitos e auditáveis.

### L7 — Desalinhamento idiomático entre OCR e centroides

A definição operacional aceita documentos em português, inglês e
espanhol (§5.2), e o PaddleOCR, mesmo configurado em `pt`, costuma
extrair texto razoável em outras línguas latinas. O problema é que os
centroides do classificador textual foram construídos quase 100% com
documentos em português — os templates CFM, LME federal, encaminhamento
SE, hemograma Hematosul, e só 1 sintético em inglês (o
`synthetic_laudo_raiox`). O centroide positivo está enviesado para o
léxico médico em pt-br.

Na prática, um documento clínico legítimo em inglês ou espanhol pode
produzir similaridade baixa com esse centroide mesmo com texto extraído
corretamente. A branch visual (CLIP, treinada majoritariamente em
inglês) ajuda a compensar, mas a fusão pode acabar rejeitando.

Para resolver em produção: incluir 20-30 documentos clínicos reais por
idioma no conjunto dos centroides, ou manter centroides separados por
idioma e despachar usando o detector de língua do OCR.

### L6 — Heterogeneidade entre estratégias

Templates preenchidos têm qualidade controlada; reais variam por fonte;
self-generated dependem do método. Avaliação reporta resultados
estratificados por `data_strategy` para tornar isso visível.

## Como interpretar as métricas

Com N=41:

- F1 reportado tem intervalo de confiança amplo (ver Wilson 95% no
  experiment-log)
- Δ entre configurações < 0.04 não é estatisticamente significativo
- Análise qualitativa dos erros é mais informativa que diferenças
  numéricas pequenas
- Recall 1.0 em N=23 positivos significa "0 falsos negativos nesta
  amostra", não "recall 100% em produção"

Em produção, com dataset real maior, espera-se F1 absoluto diferente do
reportado aqui — e principalmente diferença no padrão de FN/FP, já que
o viés sintético some.

## Referências

- Definição operacional: `docs/01-spec/definicao-documento-clinico-valido.md`
- Casos de borda pré-registrados: `docs/03-testes/casos-de-borda-pre-registrados.md`
- Experimentos: `docs/04-experimentos/experiment-log.md`
- ADR-001 (centroide com LOO): `docs/02-decisoes/ADR-001-pre-treinado-vs-treinar.md`
