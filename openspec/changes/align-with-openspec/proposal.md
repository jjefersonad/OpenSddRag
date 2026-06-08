# align-with-openspec

## Why

O OpenSddRag replica o fluxo do OpenSpec original (Fission-AI/OpenSpec) mas usando um MCP Server com PostgreSQL/pgvector como backend, em vez de arquivos locais. Uma análise comparativa identificou que o sistema atual tem gaps estruturais em relação ao OpenSpec original — alguns são bugs, outros são conceitos que existem no OpenSpec mas não foram traduzidos corretamente para o modelo de banco de dados. Como o objetivo declarado é replicar o mesmo fluxo para múltiplos projetos via MCP Server, esses gaps comprometem a fidelidade e a confiabilidade do sistema.

## What Changes

- **BUGFIX** Substituir replace total de `metadata` no `update_artifact` por merge JSONB — preserva campos existentes como `is_delta`, `capability`, `change_name` ao atualizar apenas `status`
- **BUGFIX** Adicionar UNIQUE constraint em `artifact_relationships(source_id, target_id, relationship_type)` para prevenir vínculos duplicados
- **BUGFIX** Corrigir `/opsr:apply` para buscar tasks com status `draft` OU `active` — evita tasks "orphaned" em `active` entre sessões
- **FEATURE** Formalizar o conceito de "spec principal" (fonte da verdade do sistema) separado de "delta spec" (escopo da change) — alinhado com a distinção `openspec/specs/` vs `openspec/changes/<name>/specs/` do OpenSpec original
- **FEATURE** Expandir `/opsr:propose` para criar scaffolding completo da change (proposal + esboços de design + specs por capability) em um único comando — replicando o comportamento do `/opsx:propose`
- **CLEANUP** Remover `ArtifactType.change` do enum Python, SQL e inputSchema do MCP — tipo nunca usado por nenhum comando, causa confusão ao modelo
- **IMPROVEMENT** Adicionar validação estrutural para artefatos `task` no `_validate()` — checar presença de `## Goal` e `## Acceptance Criteria`

## Capabilities

### New Capabilities

- **main-spec-as-source-of-truth** — Specs sem `change_name` são specs principais (canônicas do sistema); specs com `change_name + is_delta=true` são deltas. O `/opsr:spec` cria ou atualiza a spec principal além do delta. O `/opsr:sync` mescla o delta na principal e descarta o delta.
- **full-scaffolding-on-propose** — `/opsr:propose` passa a criar, além do proposal, esboços (draft) de design e specs para cada capability listada na seção `## Capabilities`, replicando o comportamento do `/opsx:propose` do OpenSpec original.

### Modified Capabilities

- **update-artifact** — Merge JSONB em vez de replace ao atualizar `metadata`
- **link-artifacts** — Idempotente via UNIQUE constraint no banco
- **apply-command** — Busca tasks `status IN ('draft', 'active')` em vez de só `draft`
- **validate-artifact** — Validação estrutural para tipo `task` (seções obrigatórias)
- **artifact-types** — Remoção do tipo `change` (dead code)

## Impact

- `mcp-server/src/opensddrag/db/migrations/` — nova migration: UNIQUE constraint em `artifact_relationships`, função de merge JSONB
- `mcp-server/src/opensddrag/db/repository.py` — `update_artifact` usa merge JSONB; `link_artifacts` trata conflito corretamente
- `mcp-server/src/opensddrag/mcp/server.py` — remove `change` do enum nos inputSchemas; melhora `_validate()` para tasks
- `mcp-server/src/opensddrag/models/artifact.py` — remove `ArtifactType.change`
- `client/src/templates/commands/index.js` — atualiza `/opsr:propose` (scaffolding completo), `/opsr:apply` (busca active+draft), `/opsr:spec` (cria/atualiza spec principal)
- Sem breaking changes para projetos existentes que usam o MCP Server — a migration é aditiva; artefatos existentes continuam funcionando
