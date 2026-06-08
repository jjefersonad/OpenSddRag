## 1. Atualizar template do Step 5 (spec skeleton) no /opsr:propose

- [x] 1.1 Em `client/src/templates/commands/index.js`, localizar o bloco do Step 5 ("Create spec drafts for each capability") no template da função `propose`
- [x] 1.2 Adicionar imediatamente antes do bloco de código `create_artifact` do Step 5 a linha:
  `**IMPORTANT: copy the template content VERBATIM into the \`content\` parameter — do NOT replace [TODO] markers with generated requirements, scenarios, or domain-specific rules. This step is scaffolding only; content is added by /opsr:spec.**`
- [x] 1.3 Verificar que a instrução aparece dentro do template string (entre backticks) no arquivo JS e não na lógica externa

## 2. Atualizar template do Step 6 (design skeleton) no /opsr:propose

- [x] 2.1 Localizar o bloco do Step 6 ("Create design skeleton") no mesmo template
- [x] 2.2 Adicionar imediatamente antes do bloco de código `create_artifact` do Step 6 a linha:
  `**IMPORTANT: copy the template content VERBATIM — do NOT replace [TODO] markers with generated technical decisions, architecture choices, or risk assessments. Design content is added by /opsr:design.**`

## 3. Regenerar o arquivo de comando instalado

- [x] 3.1 Rodar `node bin/opensddrag.js init --yes` (a partir de `client/`) ou o comando equivalente que regenera `.claude/commands/opsr/propose.md` no diretório do projeto cliente, para que o arquivo instalado reflita o template atualizado
- [x] 3.2 Confirmar que `.claude/commands/opsr/propose.md` contém as novas linhas `**IMPORTANT**` nos Steps 5 e 6

## 4. Verificação manual

- [x] 4.1 Rodar `/opsr:propose test-hallucination-fix` num projeto de teste com uma capability de autenticação (ex.: "user-auth") e verificar que o artefato spec criado contém apenas `[TODO]` literais, sem regras JWT ou requisitos inferidos
- [x] 4.2 Verificar que o artefato design criado contém apenas seções `[TODO]`, sem decisões técnicas geradas
