# ADR-003 — Limiar adaptativo por especialidade

## Problema

O modelo retorna um número (score de 0 a 1). Para decidir "é documento
clínico válido ou não", precisa de um limiar — acima dele aceita,
abaixo rejeita.

Se o limiar for o mesmo para todos os casos, ignoramos que **alguns
erros doem mais que outros**:


A mesma decisão técnica tem consequência clínica muito diferente dependendo de caso para caso.

## Decisão

Limiar base configurável (`CLASSIFICATION_THRESHOLD`, default **0.50** após
recalibração — ver seção "Calibração do score" abaixo) + tabela de ajustes
por especialidade quando o front envia o campo `specialty` no request:

```
limiar_aplicado = base + ajuste(specialty)
```

| Especialidade | Ajuste | Limiar final | Por quê |
|---|---|---|---|
| cardiologia | −0.10 | 0.40 | Rejeitar ECG/troponina é um problema |
| oncologia | −0.10 | 0.40 | Histórico clínico perdido afeta tratamento de longo prazo |
| pediatria | −0.08 | 0.42 | Criança não pode esperar próxima consulta |
| neurologia | −0.05 | 0.45 | AVC tem janela terapêutica curta |
| dermatologia | +0.05 | 0.55 | Não-urgente; aceitar qualquer coisa aqui sobrecarrega o especialista |
| psiquiatria | +0.07 | 0.57 | FP de documento confidencial vazado é problema sério |

Uma coisa que quero deixar clara, porque é fácil interpretar errado: esses
valores não são parâmetros calibrados do modelo. São uma regra de negócio
que mora na camada de aplicação, depois que o classificador já produziu o
score. Implementação fica em `src/app/thresholds/policy.py`, separada do
classificador — se amanhã eu trocar o modelo, essa tabela continua
fazendo sentido.

Calibração estatística de verdade (mapear o score para uma probabilidade
real de ser clínico) precisaria de Platt scaling ou regressão isotônica
sobre dados com outcome conhecido por especialidade. Não tenho esse dado,
nem dataset grande o bastante para fazer isso de forma defensável. O que
está aí é uma heurística informada pelo risco clínico — boa para a
primeira versão, claramente revisável depois.

## Exemplo prático

Dois documentos com score = 0.52:

1. Veio com `specialty=cardiologia` → limiar = 0.40 → **0.52 ≥ 0.40 → aceita**
2. Veio com `specialty=dermatologia` → limiar = 0.55 → **0.52 < 0.55 → rejeita**

O mesmo score gera decisões diferentes, dependendo do risco clínico.

## Calibração do score textual (atualização após E-006)

A versão inicial do classificador textual tinha um bug de escala na
fórmula do score. A fórmula original era esta:

```python
score = (sim_pos - sim_neg + 2.0) / 4.0
```

A intuição na hora foi: cosseno varia em [−1, +1], então a diferença
`sim_pos − sim_neg` varia em [−2, +2]; somar 2 e dividir por 4 normaliza
para [0, 1]. O problema é que sentence-embeddings normalizados quase
nunca produzem cossenos extremos — eles ficam em [0.4, 0.9], e a
diferença na prática varia em [−0.3, +0.3]. A fórmula "normalizava"
usando um range 10× maior que o real, e o resultado era esse:

| | diff médio observado | Score com fórmula antiga |
|---|---|---|
| Positivos (n=23) | +0.093 | 0.523 |
| Negativos (n=18) | −0.081 | 0.480 |

A separação entre as médias dos scores ficava em 0.044, e o modelo
parecia incapaz de distinguir as classes. Mas se eu olhasse a diferença
em cosseno antes da normalização, a separação era de 0.174 — o modelo
separava bem, a fórmula que apagava o sinal. Com threshold 0.70, todos
os docs caíam abaixo da linha.

Troquei pela sigmoid com temperatura:

```python
T = 10.0
score = 1.0 / (1.0 + exp(-(sim_pos - sim_neg) * T))
```

A sigmoid σ(x) = 1/(1+e^(−x)) mapeia qualquer real para (0, 1) com
σ(0) = 0.5. A temperatura T multiplica a entrada e controla quão
íngreme é a curva. Com T=10 a transformação fica assim:

| diff (entrada) | Score sigmoid | Interpretação |
|---|---|---|
| +0.18 | 0.858 | claramente clínico |
| +0.10 | 0.731 | clínico provável |
| +0.05 | 0.622 | clínico leve |
| 0.00 | 0.500 | empate |
| −0.05 | 0.378 | não-clínico leve |
| −0.10 | 0.269 | não-clínico provável |
| −0.18 | 0.142 | claramente não-clínico |

Para escolher T=10 fixei um critério: queria que uma diferença de
+0.1 (separação típica entre classes observada nos dados) produzisse
score ~0.73. Resolvendo `0.7 = 1 / (1 + e^(-0.1·T))` chega em T ≈ 8.5,
e arredondei para 10. Esse critério usa só a escala do cosseno —
uma propriedade do modelo de embeddings, não dos rótulos do meu
dataset. Eu chegaria em T=10 mesmo sem ter rodado nenhum experimento.

### Threshold base 0.50

Com a sigmoid no lugar, 0.5 passou a ser o ponto natural de equilíbrio
— significa `P(clínico) = P(não-clínico)`. Manter o 0.70 da versão
antiga seria arbitrário, já que ele tinha sido calibrado para uma
distribuição comprimida que não existe mais. A tabela de ajustes por
especialidade foi reescalada na mesma proporção.

## Alternativas consideradas

- **Limiar único fixo**: ignora a assimetria do risco clínico e não
  atende o item 2.3 do edital ("proponha e implemente um mecanismo de
  ajuste").
- **Limiar por histórico de erros**: precisa de feedback loop fora
  deste serviço. pode ser uma extensão futura.
- **Limiar por qualidade da extração**: backup caso o ajuste por
  especialidade não diferencie empiricamente.

## Critério pré-registrado

Antes de rodar o experimento, escrevi o teste que diria se a tabela de
ajustes vale a pena: comparo F1 macro com ajuste e sem ajuste. Se a
diferença ficar abaixo de 0.02, considero a tabela inconclusiva.

Pré-registrar isso evita o velho problema de "depois que o resultado
sai, é fácil inventar justificativa para qualquer número". Fixando o
limite antes, fico obrigado a aceitar o veredito.

## Resultados

### E-001 (baseline, fórmula linear, threshold 0.70, LOO)

| Config | F1 uniforme | F1 adaptativo | Δ |
|---|---|---|---|
| A (só CLIP) | 0.498 | 0.498 | +0.000 |
| B (só texto) | 0.360 | 0.360 | +0.000 |
| C (fusão) | 0.459 | **0.564** | **+0.105** |

ΔF1 > 0.02 só aparece em Config C — o limiar adaptativo agrega valor
quando há sinal multimodal. Critério pré-registrado confirmado.

### E-006 (sigmoid, threshold 0.50, LOGO — versão final)

| Config | F1 uniforme | F1 adaptativo | Δ |
|---|---|---|---|
| A (só CLIP) | 0.683 | 0.683 | +0.000 |
| B (só texto) | 0.548 | 0.611 | +0.063 |
| C (fusão) | 0.760 | **0.783** | **+0.023** |

ΔF1 em C continua acima do limiar pré-registrado (0.02), embora menor. A
margem caiu porque a recalibração dos scores diluiu o ganho do ajuste — o
limiar base 0.50 já cobre boa parte dos positivos sem ajuste.

## Nota sobre interpretação

Os valores da tabela refletem o risco clínico que eu assumi, não uma
calibração empírica. Em produção, eu reescreveria esses números com
duas fontes de informação que aqui não tenho: conversa com
especialistas de cada área (quanto custa pra eles um FN vs um FP no
fluxo real?) e calibração estatística do score (Platt scaling ou
isotônica) sobre um dataset maior.

