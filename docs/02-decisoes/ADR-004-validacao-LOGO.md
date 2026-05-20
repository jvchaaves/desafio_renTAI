# ADR-004 — Validação por Leave-One-Group-Out

## Problema

Dataset pequeno (41 docs) com famílias de templates:

| Grupo | Documentos |
|---|---|
| cfm_atestado | v1, v2, v3, _em_branco, _com_marca_amostra |
| lme_federal | v1, v2, v3, _fake_scan |
| encaminhamento_se | v1, v2, v3, _fake_scan |
| cfm_receituario | v1, v2, v3 |
| goiania_laudo_pericial | v1, v2, v3 |
| hematosul_hemograma | original, _fake_scan |

Várias variações compartilham o mesmo layout/header — só nomes, datas e CPFs
diferem.

## O que é LOO (Leave-One-Out Cross-Validation)

Forma de avaliar um classificador quando o dataset é pequeno demais para
separar treino/teste fixos. Com N documentos, você faz N rodadas:

```
Dataset: [A, B, C, D, E]
Rodada 1: treina com [B,C,D,E], testa em A
Rodada 2: treina com [A,C,D,E], testa em B
...
```

Cada doc é avaliado uma vez como "novo", com os outros N−1 como referência.
Aproveita 100% dos dados, mas tem um problema quando há documentos parecidos.

## O que é LOGO (Leave-One-Group-Out)

Mesma ideia, mas agrupa documentos por origem antes:

```
Grupo "cfm_atestado":   [v1, v2, v3, _em_branco, _com_marca_amostra]
Grupo "lme_federal":    [v1, v2, v3, _fake_scan]
Grupo "scielo_hemograma": [scielo_hemograma]

Rodada 1: tira grupo cfm_atestado inteiro → testa nos 5 docs dele
Rodada 2: tira grupo lme_federal inteiro → testa nos 4 docs dele
...
```

O treino nunca contém um irmão do doc testado.

## Por que LOO superestima neste dataset

Quando o doc avaliado é `cfm_atestado_v1`, o LOO deixa `v2` e `v3` no
treino. Os centroides continuam carregando o sinal do template
"atestado CFM" — cabeçalho idêntico, mesmas seções, mesma frase
"Eu, Dr. X, CRM/Y, atesto que...". O classificador acerta com
facilidade, mas não porque entendeu que é um atestado: ele já tinha
visto o template.

Em produção um doc novo é realmente novo. Não tem dois irmãos no
treino para puxar o centroide pra perto. LOGO simula isso: ao avaliar
`cfm_atestado_v1`, todos os 5 docs do grupo saem do treino, e o
centroide perde qualquer referência a atestados CFM.

## Decisão

LOGO como validação principal. LOO mantido como comparação para
documentar o leakage por template.

Implementação em `src/app/evaluation/runner.py:_group_id()`:
- regex no filename remove sufixos `_v1/v2/v3`, `_fake_scan`, `_em_branco`,
  `_com_marca_amostra`, `_anonimo`, `_modelo[N]`
- 41 docs → 26 grupos
- 6 grupos com >1 doc são as famílias de templates listadas acima

## Resultado empírico

E-006, LOGO comparado ao LOO sob a mesma configuração:

| Config | LOO F1 macro | LOGO F1 macro | Δ |
|---|---|---|---|
| A (só CLIP) | 0.683 | 0.683 | 0.000 |
| B (só texto) uniform | 0.696 | **0.548** | **−0.149** |
| B (só texto) adaptive | 0.696 | 0.611 | −0.085 |
| C (fusão) uniform | 0.783 | 0.760 | −0.023 |
| C (fusão) adaptive | 0.783 | 0.783 | 0.000 |

## Leitura

A queda de 0.149 em B é a parte que importa: confirma que o
classificador textual estava se beneficiando de ter os irmãos do
mesmo template no treino. Sob LOGO, ele perde essa muleta.

C não caiu porque a branch visual usa CLIP zero-shot, treinado pela
OpenAI em ~400M de pares imagem-texto que não têm nada a ver com o
nosso dataset. Não tem o que vazar entre folds, e quando o sinal
textual degrada, o CLIP segura sozinho. A não muda porque nem usa
LOO — ela só depende do CLIP, que é independente dos nossos dados.

## Limitações de LOGO neste dataset

LOGO não é perfeito aqui. Os grupos são derivados por heurística
(regex no filename), e se dois templates diferentes tiverem layouts
parecidos, o leakage residual não vai sumir. Vários grupos têm um
doc só — nesses casos, LOGO acaba virando LOO. E mesmo sob LOGO o N
pequeno mantém o intervalo de Wilson amplo (o CI 95% para recall
23/23 é [0.857, 1.000]).

Para validar de verdade, precisaria de dataset maior, com fontes
genuinamente diversas — hospitais distintos, períodos distintos. Não
é viável em dois dias.

## Referências

- Sklearn doc sobre LeaveOneGroupOut:
  https://scikit-learn.org/stable/modules/cross_validation.html#leave-one-group-out
- Reescala dos scores que motivou o reexame: ADR-003
- Limitação L1 (templates compartilhados): `docs/07-confianca/limitacoes-do-dataset.md`
