## Context

O OpenSddRag replica o fluxo do OpenSpec (Fission-AI/OpenSpec) usando PostgreSQL/pgvector como backend persistente em vez de arquivos locais. Uma análise comparativa entre o OpenSpec original e a implementação atual identificou 7 gaps — 3 são bugs e 4 são features de alinhamento. Este design documenta as decisões técnicas para corrigir cada gap sem breaking changes para projetos existentes.

Estado atual relevante:
- `repository.py`: `update_artifact` usa `SET metadata = %s::jsonb` (replace total)
- `repository.py`: `link_artifacts` tem `ON CONFLICT DO NOTHING` sem UNIQUE constraint real
- `server.py`: `_validate()` não verifica estrutura de `task`
- `models/artifact.py`: `ArtifactType.change` nunca usado por nenhum comando
- Comando `/opsr:apply`: `list_artifacts(type="task", status="draft")` — ignora tasks `active`
- Nenhuma distinção formal entre "main spec" e "delta spec" na camada de repositório

## Goals / Non-Goals

**Goals:**
- Corrigir os 3 bugs identificados (metadata replace, link duplicates, orphaned active tasks)
- Formalizar o conceito de main spec como fonte da verdade, alinhado com `openspec/specs/` do OpenSpec original
- Expandir `/opsr:propose` para criar scaffolding completo (proposal + design + specs)
- Remover dead code (`ArtifactType.change`)
- Adicionar validação estrutural para tasks
- Zero breaking changes para projetos existentes que já usam o MCP Server

**Non-Goals:**
- Reescrever o schema inteiro
- Migrar artefatos existentes para o novo formato de main spec (retroativo)
- Adicionar commands `/opsx:new`, `/opsx:bulk-archive` (paridade total com OpenSpec — escopo futuro)
- Mudar o modelo de embedding ou a dimensão dos vetores

## Decisions

### Decisão: Merge JSONB via operador `||` no SQL

**Escolhido:** Implementar o merge de metadata como `metadata = metadata || %s::jsonb` na query de UPDATE, com `jsonb_strip_nulls` para suporte a remoção de chaves via `null`.

**Alternativas consideradas:**
- Merge em Python antes do UPDATE — rejeitado: requer um SELECT antes de cada UPDATE (2 round-trips), introduz race conditions entre leituras e escritas concorrentes
- `jsonb_set` por chave — rejeitado: exige saber quais chaves atualizar em tempo de query; não funciona para payloads dinâmicos

**Como aplicar:**
```sql
UPDATE artifacts
SET metadata = jsonb_strip_nulls(metadata || %s::jsonb),
    updated_at = NOW()
WHERE project_id = %s AND name = %s
```

---

### Decisão: UNIQUE constraint como nova migration (002)

**Escolhido:** Criar `mcp-server/src/opensddrag/db/migrations/002_fix_relationships_and_types.sql` que:
1. Deduplica `artifact_relationships` antes de adicionar o constraint
2. Adiciona `UNIQUE (source_id, target_id, relationship_type)`
3. Altera o ENUM `artifact_type` removendo `change` (com guard se existirem dados)

**Alternativas consideradas:**
- Inlinar na migration 001 — rejeitado: a migration 001 já foi aplicada em ambientes existentes; recriar iria exigir rollback total
- Deduplicação em Python antes de aplicar o constraint — rejeitado: mais frágil que SQL nativo

**Deduplicação antes do constraint:**
```sql
DELETE FROM artifact_relationships a
USING artifact_relationships b
WHERE a.id > b.id
  AND a.source_id = b.source_id
  AND a.target_id = b.target_id
  AND a.relationship_type = b.relationship_type;
```

---

### Decisão: Main spec identificada por metadata, sem nova coluna

**Escolhido:** Manter a distinção main spec vs delta spec via `metadata.is_delta` (boolean) e `metadata.change_name` (presente ou ausente). Não adicionar coluna `is_delta` à tabela `artifacts`.

**Alternativas consideradas:**
- Adicionar coluna `is_delta BOOLEAN` na tabela — rejeitado: migration mais pesada, e a semântica já está capturada em metadata; adicionar uma coluna para um único boolean não justifica o schema change neste momento
- Tipo separado `spec_main` vs `spec_delta` no ENUM — rejeitado: quebraria todos os `list_artifacts(type="spec")` existentes

**Consequência:** O repositório não precisa mudar. A distinção é responsabilidade dos comandos MCP e da lógica de sync. Quando necessário, `search_semantic` pode receber `type="spec"` e a AI filtra por `metadata.is_delta` no resultado.

---

### Decisão: `/opsr:propose` cria artefatos skeleton via `create_artifact`

**Escolhido:** O comando `/opsr:propose` expandido chama `create_artifact` com `status="draft"` para design e para cada capability da seção `## Capabilities`. O conteúdo dos skeletons usa o template padrão com marcadores `[TODO: ...]`.

**Alternativas consideradas:**
- Criar os skeletons só quando o usuário rodar `/opsr:spec` e `/opsr:design` — status quo, rejeitado porque não replica o comportamento do `/opsx:propose`
- Criar skeletons via um novo tool `scaffold_change` no MCP server — rejeitado: desnecessário, `create_artifact` já serve; a lógica de scaffolding pertence ao command template, não ao server

---

### Decisão: Remoção do tipo `change` via ALTER TYPE com guard

**Escolhido:** A migration 002 usa um bloco `DO $$ ... $$` para checar se existem rows com `type='change'` antes de executar o `ALTER TYPE`. Se existirem, a migration faz RAISE EXCEPTION com mensagem clara.

**Consequência:** Operadores que rodarem a migration em bases com dados `change` precisarão fazer cleanup manual primeiro. A migration documenta o SQL de cleanup.

## Risks / Trade-offs

| Risco | Mitigação |
|---|---|
| Migration 002 falha em produção se houver `type='change'` artifacts | Guard com RAISE EXCEPTION + documentação do cleanup SQL |
| Merge JSONB `\|\|` concatena em vez de deep-merge (sem recursão em objetos aninhados) | Todos os metadados atuais são flat (string/bool) — sem objetos aninhados; documentar limitação |
| `link_artifacts` com `ON CONFLICT DO NOTHING` retorna `None` na linha após conflito | Ajustar para retornar o row existente via `SELECT` após conflito, ou aceitar retorno vazio sem erro |
| Skeletons criados pelo propose podem ser sobrescritos acidentalmente se o usuário rodar propose duas vezes | Checar existência antes de criar (`read_artifact`) e pular se já existir |

## Migration Plan

1. Parar o MCP server (docker compose stop ou processo stdio)
2. Aplicar `002_fix_relationships_and_types.sql` via `opensddrag init` (que roda as migrations pendentes)
3. Verificar: `SELECT COUNT(*) FROM artifact_relationships GROUP BY source_id, target_id, relationship_type HAVING COUNT(*) > 1` deve retornar 0
4. Atualizar `models/artifact.py`, `server.py`, `repository.py` e `client/src/templates/commands/index.js`
5. Reiniciar o MCP server
6. Rollback: restaurar backup do banco + reverter código (a migration é destrutiva para o ENUM se `change` type for removido)

## Open Questions

- [ ] O `link_artifacts` deve retornar o relationship existente em caso de conflito (mais informativo) ou apenas retornar silenciosamente? Atualmente retornaria `None` no `fetchone()` — isso quebra o `ArtifactRelationship(**row)` se `row` for `None`.
- [ ] Main specs devem ter `status="active"` permanentemente (distinguindo de `draft` temporário de change)? Ou `draft` para ambos e a distinção fica só no metadata?
