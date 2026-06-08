## 1. Migration de banco (002)

- [x] 1.1 Criar `mcp-server/src/opensddrag/db/migrations/002_fix_relationships_and_types.sql` com: deduplicação de `artifact_relationships`, UNIQUE constraint em `(source_id, target_id, relationship_type)`, e remoção do valor `change` do ENUM `artifact_type` com guard de segurança
- [x] 1.2 Testar a migration em banco limpo: `docker compose up -d && opensddrag init` deve rodar sem erros
- [x] 1.3 Verificar que a UNIQUE constraint está ativa: `SELECT indexname FROM pg_indexes WHERE tablename='artifact_relationships'` deve retornar o novo índice

## 2. Bugfix: metadata merge em update_artifact

- [x] 2.1 Atualizar `update_artifact` em `mcp-server/src/opensddrag/db/repository.py` para usar `metadata = jsonb_strip_nulls(metadata || %s::jsonb)` no lugar de `metadata = %s::jsonb`
- [x] 2.2 Verificar que um artifact com `metadata={"is_delta": true, "capability": "auth"}` após `update_artifact(status="archived", metadata={"archived_at": "2026-06-06"})` retém `is_delta` e `capability` no banco

## 3. Bugfix: link_artifacts idempotente

- [x] 3.1 Atualizar `link_artifacts` em `repository.py` para tratar o caso em que `ON CONFLICT DO NOTHING` não retorna nenhuma row: fazer um SELECT do relacionamento existente como fallback antes de retornar `ArtifactRelationship`
- [x] 3.2 Verificar que chamar `link_artifacts` duas vezes com os mesmos parâmetros não duplica rows na tabela e não levanta exceção

## 4. Bugfix: apply-command busca active + draft

- [x] 4.1 Atualizar o template do comando `/opsr:apply` em `client/src/templates/commands/index.js` (Step 2) para chamar `list_artifacts(type="task", status="draft")` E `list_artifacts(type="task", status="active")` e combinar os resultados, priorizando tasks `active`
- [x] 4.2 Atualizar o texto de instrução do Step 3 para selecionar tasks `active` primeiro (retomar sessão interrompida), depois `draft` em ordem de dependência

## 5. Cleanup: remover ArtifactType.change

- [x] 5.1 Remover `change = "change"` de `ArtifactType` em `mcp-server/src/opensddrag/models/artifact.py`
- [x] 5.2 Remover `"change"` dos enums `type` nos `inputSchema` de `create_artifact`, `list_artifacts`, `search_semantic` em `mcp-server/src/opensddrag/mcp/server.py`

## 6. Melhoria: validação estrutural de tasks

- [x] 6.1 Atualizar a função `_validate()` em `mcp-server/src/opensddrag/mcp/server.py` para checar que artifacts de `type="task"` contêm as strings `## Goal` e `## Acceptance Criteria` no conteúdo, adicionando issues descritivos se ausentes

## 7. Feature: main spec como fonte da verdade

- [x] 7.1 Atualizar o template do comando `/opsr:spec` em `client/src/templates/commands/index.js` para: antes de criar uma spec delta, buscar via `search_semantic` se já existe uma main spec para a capability (metadata.is_delta=false); se não existir, criar também a main spec com `metadata={"capability": "<name>", "is_delta": false}`
- [x] 7.2 Atualizar o template do comando `/opsr:sync` para, após mesclar o delta na main spec, chamar `update_artifact` na main spec com o conteúdo merged e marcar o delta como `status="archived"`

## 8. Feature: scaffolding completo no propose

- [x] 8.1 Atualizar o template do comando `/opsr:propose` em `client/src/templates/commands/index.js` para, após criar o proposal artifact (Step 4 atual), iterar sobre as capabilities da seção `## Capabilities` e chamar `create_artifact(type="spec", status="draft", metadata={"is_delta": true, ...})` para cada uma — verificando antes com `read_artifact` para não sobrescrever specs existentes
- [x] 8.2 Criar também um artifact de design skeleton: `create_artifact(name="<change-name>-design", type="design", status="draft", content="<template com [TODO] placeholders>")` ao final do propose, se ainda não existir

## 9. Validação final

- [x] 9.1 Reiniciar o MCP server e rodar um fluxo completo de ponta a ponta: `propose → spec → design → tasks → apply → verify → archive` num projeto de teste, verificando que metadata é preservado após archive, que links não duplicam, e que tasks orphaned são recuperadas pelo apply
