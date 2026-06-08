# fix-propose-spec-hallucination

## Why

O comando `/opsr:propose` (Step 5) instrui o agente a criar artefatos `spec` do tipo rascunho com marcadores `[TODO: ...]` como conteúdo placeholder. Porém, o agente (Claude) interpreta esses marcadores como convites para preenchimento e infere conteúdo real — como regras JWT — a partir do nome da capability ou do contexto da proposta, mesmo sem nenhuma solicitação do usuário. Isso viola o contrato do fluxo SDD: a fase `propose` deve apenas registrar intenção, nunca gerar requisitos.

## What Changes

- **BUGFIX** Atualizar o template do comando `/opsr:propose` para proibir explicitamente o preenchimento de conteúdo nos esboços de spec — o agente deve inserir literalmente os marcadores `[TODO]` sem substituí-los
- **BUGFIX** Atualizar o template do comando `/opsr:propose` para proibir explicitamente o preenchimento de conteúdo no esboço de design — mesmo princípio

## Capabilities

### New Capabilities

- `propose-skeleton-enforcement`: Garantia de que os artefatos de spec e design criados pelo `/opsr:propose` contenham apenas marcadores de placeholder literais (`[TODO]`), sem conteúdo gerado pelo agente

### Modified Capabilities

- `full-scaffolding-on-propose`: O comportamento de criação de scaffolding permanece, mas com restrição explícita de que o agente não pode preencher conteúdo real nos esboços

## Impact

- `client/src/templates/commands/index.js` — template do comando `/opsr:propose` (Steps 5 e 6): adicionar instrução explícita de não substituir `[TODO]` por conteúdo real
- Nenhuma mudança no banco de dados, no MCP server ou na CLI Python
- Sem breaking changes — a mudança é apenas no texto de instrução do comando
