# Definição operacional — "documento clínico válido"

Esta é a referência usada para rotular o dataset, escolher os prompts de
classificação e definir a política de limiar.

## Princípio

Documento produzido no contexto de assistência à saúde humana, com
informação clínica estruturada sobre paciente identificável, emitido por
profissional de saúde regulamentado ou sistema clínico, em formato
apropriado para análise por outro profissional.

Quatro elementos precisam estar presentes:

1. Contexto de assistência à saúde (não administrativo, comercial, educacional)
2. Conteúdo clínico estruturado (não menção tangencial)
3. Paciente identificável (direto ou pelo contexto do upload)
4. Emissor reconhecível (profissional regulamentado ou sistema clínico)

## Critérios inclusivos (todos devem aplicar)

- **C1** Conteúdo clínico estruturado: dados objetivos (medidas, valores),
  avaliação subjetiva (impressão diagnóstica) ou plano (prescrição, conduta).
- **C2** Paciente identificável: nome, registro ou contexto. Documento
  completamente anônimo é tratado como inválido (default conservador).
- **C3** Emissor reconhecível: profissional regulamentado (CRM, CRO,
  COREN, CRP, CRN, CREFITO, etc.) ou layout institucional (papel
  timbrado, carimbo, marca de hospital/clínica/laboratório).
- **C4** Formato apropriado: PDF nativo, PDF escaneado, foto bem-feita
  de documento físico ou imagem direta de exame. NÃO: screenshot de
  app, foto de tela de outro dispositivo, foto de monitor médico.

## Critérios exclusivos (qualquer um rejeita)

- **N1** Não-documento (selfie, foto casual, foto de objeto sem propósito documental)
- **N2** Captura indireta (screenshot, foto de tela)
- **N3** Contexto explicitamente não-clínico (contrato, fatura, recibo)
- **N4** Documento técnico não-assistencial (manual de equipamento, bula isolada)
- **N5** Fora do escopo (medicina veterinária, profissões não-regulamentadas)
- **N6** Auto-declaração de invalidade (marca d'água "AMOSTRA")
- **N7** Conteúdo educacional/científico (artigo, slide, material didático)

## Escopo

**Profissões aceitas** (saúde humana regulamentada): medicina, odontologia,
enfermagem, psicologia, nutrição, fisioterapia, fonoaudiologia, terapia
ocupacional, biomedicina, farmácia (quando atua clinicamente).

**Justificativa do escopo amplo**: o serviço atende APS no SUS, que é
multidisciplinar por design. Restringir a médicos descaracterizaria o
contexto.

**Idioma**: português é o esperado. Inglês e espanhol aceitos. Idiomas
com escrita não-latina (chinês, árabe) são tratados como inválidos por
limitação técnica do OCR/embeddings, não por critério conceitual.

## Política para zona cinza

Sistema binário (`valid` / `invalid`), default conservador: em caso de
dúvida genuína, rejeita.

Justificativa: no fluxo de teleconsultoria, FP (aceita inválido) custa
poucos segundos do especialista descartar. FN (rejeita válido) é
mitigável: o front (P01) sinaliza, o profissional reenvia. A política
adaptativa do ADR-003 inverte isso para especialidades de urgência
(cardiologia, oncologia), onde FN tem alto custo.

## Casos-limite pré-decididos

| # | Caso | Veredito | Razão |
|---|---|---|---|
| 1 | Foto de embalagem de remédio | inválido | C1, C2 falham (sem paciente, sem prescrição) |
| 2 | Receita manuscrita ilegível | válido | Formato clínico; legibilidade é problema de extração |
| 3 | Atestado em branco (template) | inválido | C1, C2 falham (sem conteúdo, sem paciente) |
| 4 | Cartão de vacinação preenchido | válido | Conteúdo + paciente + emissor |
| 5 | Print de portal médico exibindo exame | inválido | N2 (captura indireta) |
| 6 | Artigo científico médico | inválido | N7 (educacional) |
| 7 | Prontuário parcial sem identificação | inválido | C2 falha (default conservador) |
| 8 | Foto de outro celular mostrando exame | inválido | N2 |
| 9 | Manual de equipamento médico | inválido | N4 |
| 10 | Curva de febre desenhada pelo paciente | inválido | C3 falha (sem emissor profissional) |
| 11 | Documento médico antigo (1995) | válido | Atualidade não é critério |
| 12 | Foto de monitor de UTI | inválido | N2 (captura efêmera) |
| 13 | Relatório veterinário | inválido | N5 |
| 14 | PDF com marca d'água "AMOSTRA" | inválido | N6 |
| 15 | Foto bem-feita de receita física | válido | C4 cumprido (foto de objeto ≠ screenshot) |
| 16 | Documento médico em inglês | válido | Idioma aceito |
| 17 | Encaminhamento entre serviços | válido | Documento clínico-administrativo legítimo |
| 18 | Foto do paciente segurando exame | inválido | C4 falha (formato comprometido) |

## Fora do escopo (não julgamos)

- Qualidade clínica do conteúdo
- Autenticidade / detecção de falsificação
- Atualidade
- Adequação à especialidade da consulta
- Anonimização / proteção de PII
- Conformidade jurídica (CFM, ANVISA)

## Casos onde arquivo não é processável

PDF corrompido, criptografado, formato errado, imagem vazia: tratados
como `valid=false` com `reason` distinto de `non_clinical` (ver
`docs/01-spec/api-contract.openapi.yaml`, campo `reason`).
