# Casos de borda pré-registrados

Hipóteses sobre o comportamento esperado do classificador, escritas
**antes** da execução do E-001. Após a rodada, cada caso é marcado com
✅ confirmada / ❌ refutada / ⚠️ parcial.

## Por que pré-registrar

O edital (bônus de ML testing sistemático) pede casos de borda com
hipóteses explícitas antes da execução. Isso evita racionalização
posterior do resultado.

## Hipóteses

### CB-01: PDF nativo de exame laboratorial
Texto rico, layout reconhecível. **Esperado**: A, B e C aceitam com
score alto.

### CB-02: Receita manuscrita ilegível
OCR falha, mas layout visual de prescrição é reconhecível.
**Esperado**: A aceita, B rejeita, C aceita (extraction_quality baixo
→ visão domina).

### CB-03: PDF escaneado de baixa qualidade
OCR retorna texto fragmentado. **Esperado**: B fica abaixo do limiar;
C compensa pela visão.

### CB-04: Print de portal médico exibindo exame
Texto extraído é clínico (termos médicos), mas formato é screenshot.
**Esperado**: B aceita incorretamente, A rejeita ("screenshot of phone
screen"), C rejeita pela contribuição de A.

### CB-05: Selfie renomeada como `exame.pdf`
Sem texto, claramente uma pessoa. **Esperado**: todos rejeitam com
score muito baixo. Ataque adversário básico.

### CB-06: Manual de equipamento médico
Visualmente parece doc técnico médico; texto é
manual/especificação. **Esperado**: A confunde; B rejeita (vocabulário
não-clínico); C rejeita pelo texto dominar.

### CB-07: Artigo científico médico
**Esperado**: ambas branches rejeitam (texto educacional, layout de
paper).

### CB-08: Prontuário parcial sem identificação
Conteúdo clínico denso, sem paciente. **Esperado**: divergência entre
modelo (provavelmente aceita pelo conteúdo) e definição (rejeita por
C2 falhar). Candidato a entrar na análise de erros.

### CB-09: Documento médico antigo (1995)
Atualidade não é critério. **Esperado**: aceita.

### CB-10: Foto do paciente segurando exame
Documento + pessoa no enquadramento. **Esperado**: visão detecta
presença humana e reduz score; decisão apertada.

### CB-LIM-01: Documento de cardiologia próximo do limiar
Score 0.65, limiar uniforme 0.70 → rejeitado. **Esperado**: com
ajuste por especialidade (-0.10), aceito. Mostra o valor do limiar
adaptativo.

### CB-LIM-02: Documento de dermatologia próximo do limiar
Score 0.72, limiar uniforme aceita. **Esperado**: com ajuste (+0.05),
rejeitado. Mostra que adaptativo também pode endurecer.

### CB-LIM-03: ΔF1 entre uniforme e adaptativo
Hipótese: com N pequeno, Δ deve ficar abaixo de 0.02 (ruído
estatístico). Critério pré-registrado para abandono no ADR-003.

### CB-OCR-01: PaddleOCR em documento limpo
CER < 0.05 esperado. Valida que o OCR funciona quando a imagem é boa.

### CB-OCR-02: PaddleOCR em manuscrito
CER > 0.25 esperado. Justifica empiricamente a importância da branch
visual.

## Confronto com resultado (E-001)

A validação completa cada caso após a rodada está no relatório em
`docs/05-resultados/relatorio-e001.md` e na seção 5 do README.

Resumo (Config C, threshold adaptativo):
- ✅ CB-04, CB-05, CB-06, CB-07: comportamento esperado
- ✅ CB-LIM-01, CB-LIM-02: ajuste por especialidade afetou decisão
- ❌ CB-LIM-03: Δ veio em +0.105 em Config C — refutada (a fusão
  amplifica o sinal mais do que esperado para N=41)
- ❌ CB-02 (receita manuscrita): C rejeitou; CLIP não reconheceu cursiva
  como prescrição
- ⚠️ CB-08, CB-10: comportamento parcial; entram na análise de erros
- ⚠️ CB-03 (scan ruim): score baixo mesmo em C; degradação prejudicou
  todas as branches
