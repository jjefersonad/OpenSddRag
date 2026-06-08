## Context

O `/opsr:propose` cria artefatos de spec e design como esboços (status=draft) para cada capability da proposta. O template do comando fornece conteúdo com marcadores `[TODO: ...]` que devem ser preservados literalmente. Porém, o agente que executa o comando (Claude) trata esses marcadores como instruções de preenchimento e infere conteúdo real a partir do contexto — por exemplo, criando regras JWT para uma capability chamada "authentication" sem que o usuário tenha solicitado.

Estado atual do arquivo afetado: `client/src/templates/commands/index.js`, template da função `propose` (Steps 5 e 6).

## Goals / Non-Goals

**Goals:**
- Eliminar a geração de conteúdo não solicitado nos esboços criados pelo `/opsr:propose`
- Garantir que os `[TODO]` sejam copiados literalmente para o banco de dados

**Non-Goals:**
- Validar o conteúdo dos artefatos após criação (responsabilidade do `/opsr:spec`)
- Mudar o comportamento de scaffolding (ainda cria spec e design skeletons)
- Adicionar validação no MCP server ou no banco de dados

## Decisions

### Decision: correção via instrução explícita no template, não via validação pós-criação

**Chosen:** Adicionar uma linha `**IMPORTANT: copy the template content VERBATIM — do NOT replace [TODO] markers with generated content. This step is scaffolding only.**` imediatamente antes de cada bloco `create_artifact` nos Steps 5 e 6.

**Alternatives:**
- Validação no MCP server (`_validate()`) que rejeita artefatos sem `[TODO]` — rejeitado porque inverte a lógica: o artefato pode legitimamente não ter `[TODO]` se o usuário quiser fornecer conteúdo direto
- Usar delimitadores diferentes (ex.: `«TODO»`) — rejeitado porque requer mudança no template e nos exemplos existentes; a causa raiz é a ausência de instrução, não o formato do marcador

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| O agente pode ignorar a instrução mesmo com negrito | A instrução usa linguagem imperativa forte ("MUST NOT", "VERBATIM") que modelos seguem com alta confiabilidade |
| Usuários que querem fornecer conteúdo real no propose ficam confusos | A instrução é dirigida ao agente, não ao usuário; o usuário fornece conteúdo via `/opsr:spec` |
