# Registro de Uso de IA — Desafio P04 ReNTAI

Este arquivo registra como usei ferramentas de IA durante o desenvolvimento.
A ideia não é listar cada autocompletar, mas deixar claro onde a IA ajudou,
o que eu aproveitei, o que precisei corrigir e quais decisões ficaram sob
minha responsabilidade.

## 1. Ferramentas usadas

| Ferramenta | Uso principal |
|---|---|
| Claude Code | Discussão de arquitetura, revisão, organização de documentação, boilerplate e apoio na comparação de alternativas |

Usei a IA como apoio de desenvolvimento. Em geral, eu fornecia o contexto do
edital, pedia alternativas ou revisão de uma ideia, e então implementava,
testava e ajustava localmente.

## 2. Como a IA foi orientada

Os prompts normalmente continham:

- trecho ou requisito do edital;
- objetivo da etapa;
- restrições de custo e prazo;
- preferência por modelos abertos e execução local;
- necessidade de documentar decisões e limitações.

Exemplos de pedidos feitos durante o projeto:

- entender se fazia sentido treinar um modelo do zero ou usar pré-treinados;
- comparar opções para o limiar adaptativo;
- estruturar o contrato da API em FastAPI;
- criar scripts para montar um dataset reprodutível;
- revisar erros do pipeline depois de falhas em testes locais;
- gerar tabelas e relatórios a partir dos resultados.

## 3. Onde a IA ajudou mais

### Planejamento da abordagem

No começo, usei a IA para discutir o edital e organizar as opções de solução.
A recomendação inicial foi evitar treino do zero, porque o dataset exigido era
pequeno. Eu aceitei essa direção e documentei a decisão no ADR-001.

Também usei a IA para levantar alternativas de limiar adaptativo. A opção
escolhida foi começar por especialidade clínica, por ser simples de explicar
e atender diretamente ao edital. Outras opções, como histórico de erros e
qualidade de extração, ficaram documentadas como alternativas futuras.

### Estrutura da documentação

A IA ajudou a organizar a documentação em especificação, ADRs, experimentos,
resultados e limitações. Eu revisei os textos, ajustei a definição dea
"documento clínico válido" e mantive a decisão de usar uma saída binária,
porque o edital discute falsos positivos e falsos negativos.

### Código base da API

Usei a IA principalmente para revisar a estrutura esperada de uma API FastAPI
e lembrar padrões de schemas, rotas e tratamento de erro. A implementação foi
feita por mim e validada contra o contrato pedido no edital: arquivo de
entrada, score, label, justificativa, limiar aplicado e motivo da decisão.

### Dataset e scripts auxiliares

A composição do dataset, os critérios de rotulação e os casos de
borda são meus. A parte braçal de gerar os arquivos sintéticos eu
deleguei pra IA por uma razão prática: dados clínicos reais em portugues,
sem PII e com licença pra redistribuir, são raros. Datasets públicos
médicos geralmente estão em inglês ou exigem credencial; usar exame
real de algum conhecido esbarra na LGPD; e os templates oficiais (CFM,
LME federal, encaminhamento SUS) que circulam publicamente estão em
branco.

A saída foi gerar dados sintéticos de forma declarada. Pedi à IA que
escrevesse três scripts em `scripts/data_prep/`:

1. `generate_varied_templates.py` — preencher os templates oficiais (CFM,
   LME, encaminhamento, hemograma) com **nomes, CPFs, CNS, datas e CRMs
   sintéticos**, gerando 3 variações por template. Os dados sintéticos são
   gerados a partir de pools aleatórios definidos no próprio script — todos
   declarados como inventados.
2. `generate_synthetic_docs.py` — criar imagens não clínicas
   (selfie, foto de comida, pet, recibo, RG anonimizado) e alguns
   clínicos sintéticos (laudo de raio-X, cartão de vacina, evolução de
   enfermagem) via PIL/matplotlib. Foco em imagens visualmente
   reconhecíveis pelo tipo declarado, suficientes para testar a
   classificação multimodal.
3. `generate_fake_scans.py` — degradar PDFs nativos com rotação, blur,
   compressão JPEG e marca d'água "AMOSTRA" para simular fotos de papel e
   testar o critério N6 da definição operacional.

Alguns cuidados que tomei pra essa estratégia não virar uma armadilha:
cada arquivo gerado tem `data_strategy` declarado no `labels.csv`
(`template-fill`, `self-generated`, `fake-scan`, `real`), de modo que o
avaliador distingue o que é real do que é sintético sem precisar
inferir. O viés esperado dessa composição está registrado em L1 (em
`docs/07-confianca/limitacoes-do-dataset.md`), e foi exatamente o que
me levou a migrar a validação de LOO para Leave-One-Group-Out (ADR-004)
 sob LOGO, o classificador textual perde 0.149 de F1, prova
empírica de que ele estava memorizando layouts de templates. Por isso
também os números finais (F1 macro 0.783) valem para este dataset com
esta validação; em produção, com fontes diversas, o resultado
provavelmente cai.

A IA aqui foi essencial  sem ela, não conseguiria gerar dataset rotulado
em tempo viável sem violar LGPD ou redistribuir material com licença
ambígua. Os scripts permitem que o avaliador **regenere** o dataset
do zero, o que é mais transparente do que entregar arquivos opacos.

### Extração, OCR, classificadores e avaliação

Essas foram as partes mais importantes do projeto e foram implementadas e
validadas por mim. Usei a IA para discutir alternativas e revisar escolhas,
mas as decisões principais ficaram sob minha responsabilidade:

- usar `pypdf` como extração primária em PDF nativo;
- usar PaddleOCR para scans/imagens e fallback quando o PDF não tinha texto útil;
- usar embeddings com distância de centroide em vez de treinar modelo do zero;
- usar CLIP como sinal visual paralelo ao texto;
- fundir texto e visão de acordo com a qualidade da extração;
- avaliar com Leave-One-Group-Out (após identificar leakage de templates
  no LOO clássico  ver ADR-004);
- comparar threshold uniforme e adaptativo.

A escolha das métricas, a leitura dos falsos positivos/falsos negativos e a
interpretação dos resultados foram feitas por mim a partir das tabelas geradas.
Os achados principais ao longo do projeto foram: a fórmula linear do score
textual cumprimia o sinal contra a escala real do cosseno e precisou ser
substituída por sigmoid com temperatura; o LOO estava superestimando F1 por
causa das variações de template no treino, o que motivou a migração para
LOGO; e a multimodalidade (CLIP zero-shot + texto) se mostrou robusta a esse
viés, segurando o recall quando o sinal textual degrada.

## 4. O que precisei corrigir

### API do PaddleOCR

Durante a integração do OCR, testei a versão instalada do PaddleOCR e encontrei
diferenças em relação a exemplos antigos da biblioteca, como `use_angle_cls`,
`show_log` e `.ocr(..., cls=True)`. Corrigi a integração para usar
`PaddleOCR(lang="pt")` e `.predict(...)`, lendo `rec_texts` e `rec_scores` do
resultado.

### Uso de memória

Ao rodar o experimento, percebi que carregar PaddleOCR, sentence-transformers
e CLIP no mesmo processo consumia memória demais. A correção foi separar o
experimento em duas fases:

1. extração e cache dos textos/imagens;
2. classificação a partir do cache.

Essa mudança deixou o experimento mais estável e também facilitou reproduzir
os resultados.


### Threshold inicial

O threshold base `0.70` fazia sentido como escolha conservadora, mas os
resultados mostraram que ele ficou alto para a escala dos scores gerados. Por
isso a análise final aponta calibração de threshold como uma das principais
melhorias para uma versão de produção.

### Separação treino/inferência

Quando fui testar o serviço, a primeira chamada a `/v1/validate`
levava mais de 5 minutos. O orquestrador estava fazendo fit do
classificador textual sob demanda, o que envolvia rodar OCR nos 41
docs do dataset antes de responder a primeira requisição. Conversei
com a IA sobre opções, gostei da que ela propôs e implementei: gerar um
artifact pré-computado (`artifacts/centroids.npz`) em fase offline e
carregar ele no startup do FastAPI. Como efeito colateral, o servidor
deixou de depender de `data/labeled/` em runtime. Detalhes no ADR-005.

## 5. O que foi descartado

- **Treinar modelo do zero**: rejeitado por falta de dados suficientes.
- **Fine-tuning de BERT/BERTimbau**: tecnicamente possível, mas frágil com
  apenas algumas dezenas de exemplos.
- **Três rótulos (`valid`, `invalid`, `uncertain`)**: rejeitado para manter a
  avaliação binária de FP/FN pedida no edital.
- **LLM externo no caminho principal**: removido para evitar dependência de
  API externa e custo.
- **Limiar por histórico de erros**: deixado como melhoria futura, porque
  exigiria feedback de produção e armazenamento persistente.

## 6. Decisões que revisei diretamente

As decisões abaixo não foram aceitas automaticamente:

- definição operacional de documento clínico válido;
- escolha de saída binária;
- critérios para os casos ambíguos;
- composição final do dataset;
- bibliotecas de extração e OCR;
- métricas de avaliação e estratégia de validação;
- implementação do pipeline de extração/classificação;
- valores iniciais de ajuste por especialidade;
- prompts positivos e negativos do CLIP;
- interpretação dos falsos positivos e falsos negativos;
- texto final do README e dos ADRs.

## 7. Avaliação geral

A IA foi útil para acelerar partes repetitivas, levantar alternativas e revisar
documentação. As partes centrais do serviço  extração, OCR, classificação,
fusão e avaliação — foram implementadas, testadas e ajustadas por mim durante
o desenvolvimento.
