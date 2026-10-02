# Arquitetura do Backend

Referência técnica da aplicação `mcp-server/` — servidores MCP, REST e CLI em Python (modular monolith).
Arquitetura baseada no padrão **Modular Monolith** de Sebastian Buczyński ([breadcrumbscollector.tech/modular-monolith-in-python](https://breadcrumbscollector.tech/modular-monolith-in-python/)) e Clean Architecture.
Para comandos de build, portas e variáveis de ambiente, consultar [`CLAUDE.md`](../CLAUDE.md).

---

## Stack

| Tecnologia | Papel |
|---|---|
| Python 3.12+ | Linguagem do servidor |
| MCP SDK (`mcp.*`) | Protocolo MCP (tools/resources) |
| Starlette + Uvicorn | Transporte HTTP/SSE e montagem de apps |
| Typer | CLI de administração |
| psycopg (async pool) | Acesso a PostgreSQL |
| PostgreSQL + pgvector | Persistência + busca vetorial (HNSW, 384 dims) |
| sentence-transformers | Geração de embeddings (`all-MiniLM-L6-v2`) |
| pydantic / pydantic-settings | Modelos de domínio e configuração via `.env` |

---

## Princípio: modular monolith (modulith)

O servidor é **um único deployable com componentes deliberadamente separados** — não um micro-serviço distribuído e não um monólito bola-de-lama. Cada componente (conceito do artigo):

- Tem uma **API pública explícita** (use cases, facades) e **detalhes privados** que nenhuma outra camada toca (encapsulamento em nível de componente).
- Se comunica com outros componentes apenas por **chamada direta à API pública** ou por **ports (interfaces)** — nunca importando internos de outro componente.
- Expõe **DTOs** (`Request`, `Response`), nunca modelos de banco ou entidades de domínio, pelo seu limite.
- Pode ter **arquitetura interna própria**: o componente core usa Clean Architecture; os componentes de acesso a dados usam o padrão repository mais simples. O artigo recomenda limitar a 2 arquiteturas internas — é exatamente o que fazemos.

**Por que não microservices?** Os drivers arquiteturais para distribuir (scaling independente, linguagens distintas, isolamento de risco) não se aplicam: é uma ferramenta single-user, single-deploy, com um único banco. O modulith dá a separação lógica sem o custo operacional; se um dia precisar virar serviço, as fronteiras já existem e o preço de errá-las foi baixo.

---

## Estrutura de Diretórios

```
mcp-server/src/opensddrag/
├── core/                       # Componente central — Clean Architecture
│   ├── domain/                 # Entidades e regras puras (Tool, Permission, Response, Request, validation, errors)
│   ├── ports/                  # Interfaces (typing.Protocol) — única "seam" entre use cases e adapters
│   └── usecases/               # Casos de uso (ExecuteToolUseCase, ListToolsUseCase) — a API pública do core
├── infrastructure/             # Adapters concretos dos ports do core
│   ├── composition.py          # Composition root — ÚNICO módulo que importa core + infrastructure + db
│   ├── bootstrap.py            # Ciclo de vida (startup/shutdown do pool e adaptações)
│   ├── auth/                   # NoopAuthenticator, DefaultAuthorizationPolicy
│   ├── memory/                 # Rate limiter e tool registry em memória
│   ├── pg/                     # Adapters PostgreSQL (registry, rate limiter, logger, tool_executors)
│   ├── validation/             # JsonSchemaValidator (entrada e saída)
│   └── mcp_resources.py        # Resources MCP (projetos e artefatos)
├── mcp/                        # Adapter de transporte MCP (protocolo) — server.py, auth.py, context.py
├── cli/                        # Adapter de entrega CLI (typer) — wires sub-typers por domínio
├── db/                         # Camada de dados — pool async, migrations, repositories por agregado
├── embedding/                  # Serviço de embeddings (sentence-transformers)
├── models/                     # Modelos pydantic das entidades persistidas
├── config.py                   # pydantic-settings (var de ambiente / .env)
└── tests/architecture/         # Testes de arquitetura que fazem cumprir as regras de import
```

---

## Camadas e Responsabilidades

```
┌──────────────────────────────────────────────────────────────┐
│  mcp/                    ADAPTERS DE ENTREGA (interfaces)     │
│  cli/                    Protocolo MCP e CLI typer            │
│  ─ não contêm regra de negócio, só serialização/resolução    │
└──────────────────────────────┬───────────────────────────────┘
                               │ chamam (único caminho)
┌──────────────────────────────▼───────────────────────────────┐
│  core/usecases           API PÚBLICA do core                  │
│  ExecuteToolUseCase      pipeline: auth → rate-limit →        │
│  ListToolsUseCase        validate → execute → log             │
└──────────────────────────────┬───────────────────────────────┘
                               │ depende de interfaces (DIP)
┌──────────────────────────────▼───────────────────────────────┐
│  core/ports              Ports (typing.Protocol, zero impls)  │
│  core/domain             Domínio puro (DTOs, Permission, Tool)│
└──────────────────────────────▲───────────────────────────────┘
                               │ implementam os ports (DIP)
┌──────────────────────────────┴───────────────────────────────┐
│  infrastructure/         Adapters concretos                    │
│  db/                     Repositories + pool + migrations      │
│  embedding/              Serviço de embeddings                  │
└──────────────────────────────────────────────────────────────┘
```

**Regra de dependência (a Dependency Rule):** dependências apontam para Dentro/Direção ao core. `mcp/` e `cli/` dependem de `core/`; `core/` depende apenas de `core/domain` + `core/ports`; `infrastructure/` e `db/` implementam `core/ports` (inversão de dependência) — nunca o contrário.

**O que cada teste de arquitetura faz cumprir (`tests/architecture/test_imports.py`):**

| Teste | Regra |
|---|---|
| `test_domain_is_pure` | `core/domain` não importa nada de infra/transporte |
| `test_usecases_have_no_infra_or_db_imports` | `core/usecases` não importa `infrastructure/`, `db/` ou transporte |
| `test_infrastructure_only_imports_downward` | `infrastructure/` nunca importa de `mcp/`, `cli/` (composition root isento) |
| `test_mcp_adapter_does_not_import_repositories` | transporte não fala com `db/` — só com use cases |

---

## Os Ports (interfaces do core)

Todos em `core/ports/`, definidos como `typing.Protocol` — **sem nenhuma implementação**

| Port | Responsabilidade |
|---|---|
| `ToolRegistryPort` | Registro/lookup das tools disponíveis |
| `ToolExecutorPort` | Execução do corpo de uma tool por dispatcher (por `tool.name`) |
| `AuthenticationPort` | Autenticação do `Caller` |
| `AuthorizationPolicyPort` | Permissão de chamada por role/permission |
| `RateLimiterPort` | Quota por janela de tempo |
| `InputValidatorPort / OutputValidatorPort` | Validação JSON Schema (entrada/saída) |
| `LoggerPort` | Log estruturado |

O use case nunca sabe se há PostgreSQL, memória ou schema JSON: usa apenas as interfaces. Isso é a "chamada direta via classe abstrata" do artigo (payments vs auctioning platform).

---

## Composition Root — `infrastructure/composition.py`

O ponto único de montagem (equivalente ao módulo `main` do artigo): constrói todos os adapters e injeta nos use cases.

- `UseCases` — dataclass **frozen** com os use cases + adapters compartilhados (registry, authenticator, rate limiter, logger). Imutável em runtime, ninguém re-wire um port em runtime.
- `build_use_cases(settings, *, tool_executors)` — resolve automaticamente os adapters pelo modo (critério de seleção):

| Condição | Adapters selecionados |
|---|---|
| `DATABASE_URL` preenchida **e** `RATE_LIMITER != "memory"` | PostgreSQL (pg_registry, pg_rate_limiter, pg_logger) |
| `DATABASE_URL` vazia **ou** `RATE_LIMITER=memory` | Em memória (in_memory_registry, in_memory_rate_limiter) |

- `_MappingToolExecutor` — dispatcher que seleciona o executor da tool por `tool.name`. Tools sem executor falham **ruidosamente com erro estruturado** (`INTERNAL`), nunca silenciosamente com `None`.
- **Única exceção à dependência linear:** `composition.py` importa de `core/`, `infrastructure/` e `db/` simultaneamente. É o ápice do grafo, não pode ter ciclo — e está explicitamente isentado no teste de arquitetura.
- **Ciclo de vida com o `bootstrap.py`** — startup (pool de conexões + warm-up dos adapters) e shutdown idempotentes, chamados pelos adapters de entrega (`_main_stdio`, `_main_sse`).

---

## Adapter de Protocolo MCP — `mcp/server.py`

Componente de entrega que expõe 23 tools. Não contém lógica de negócio:

1. `_resolve_caller()` — extrai o project slug do contexto MCP e monta o `Caller` (DTO) com `Permission.ADMIN`.
2. `MCPServerAdapter.call_tool()` → `execute_tool.execute()` (o use case).
3. `_serialize_response()` — serializa `Response` para `TextContent` JSON. Erros viram envelope estruturado `{"error": {"code": ..., "message": ...}}`, nunca `None`.
4. **Transportes:** `stdio` (Claude Code spawn) ou `sse` (HTTP, Starlette + StreamableHTTPSessionManager). O `AuthMiddleware` protege apenas o transporte HTTP quando `AUTH_ENABLED=true`.

**Regra:** nenhuma tool importa repositories ou SQL diretamente. Qualquer nova tool passa pelo mesmo pipeline de use case, herda auth/rate-limit/validation/logging de graça.

---

## Persistência — `db/`

Camada repository **leve** (a "arquitetura simplificada" do artigo — modelos de banco como objetos, sem DDD pesado):

| Arquivo | Agregado |
|---|---|
| `connection.py` | Pool async psycopg + `run_migrations()` |
| `db/repository.py` | Artefatos (CRUD, busca semântica pgvector, relacionamentos, filtro por `flow`) |
| `db/project_repository.py` | Projetos (registro multi-tenant; `default_flow`) |
| `db/rule_repository.py` | Regras de harness (`trigger` texto livre; filtro por `flow`) |
| `db/session_repository.py` | Working context por projeto |
| `db/skill_repository.py` | Skills globais e específicas (carregam `flow`) |
| `db/trace_repository.py` | Memória episódica (execuções + embeddings) |
| `db/api_key_repository.py` | Chaves de API |
| `db/migrations/` | SQL versionado (esquema + índices pgvector HNSW); `008_multi_flow.sql` adiciona o registro de flows e tipos livres |

Os repositories retornam os modelos pydantic de `models/` — nunca rows cruas. As funções são **módulo-nível, async, e não guardam estado** (o pool é compartilhado via `connection.get_conn()`), portanto seguem o padrão "funções puras" do nível serviços do frontend.

### Flow registry (multi-flow)

O core é **domain-agnostic**: SDD é o primeiro **flow** (`flow='sdd'`), não o único.
Um flow é um pack de dados — `kinds`, `harness_triggers`, `skills`, `commands` e
uma seção de `CLAUDE.md` — sem código específico no servidor:

| Arquivo | Responsabilidade |
|---|---|
| `core/domain/flow_manifest.py` | Schema puro do manifest (`FlowManifest`, `manifest_issues`, `validate_manifest`) |
| `core/domain/flow_registry.py` | `ensure_sdd_flow`, `register_flow` (upsert idempotente em `flows`/`artifact_kinds`) |
| `core/domain/artifact_validation.py` | `validate_registered`: precedência `(flow, kind)` (built-in SDD → declarativo → fallback) |
| `db/repository.get_artifact_kind_rules` | Lê `artifact_kinds.rules` do par `(flow, kind)` |

`artifacts.type` é **texto livre** (não enum) e `artifacts`/`skills`/`project_rules`
carregam `flow`; `projects.default_flow` resolve um `flow` omitido. As tools MCP
`create_artifact`/`list_artifacts`/`search_semantic`/`get_harness_checklist` aceitam
`flow` opcional, e `register_flow` ingere um manifest. No cliente, cada fluxo vive
em `client/src/templates/flows/<slug>/` e é instalado via `init --flow`.

---

## Embeddings — `embedding/`

Componente isolado (wrapper de 3ª lib): `sentence-transformers` com modelo `all-MiniLM-L6-v2` (384 dims). Consumido pelos repositories ao persistir/re-embedar artefatos e traces. Isolado em camada própria porque é o único acoplamento a um modelo de ML — a troca do modelo é uma mudança interna do componente, invisível ao resto.

---

## Onde colocar o quê

- Nova tool (fluxo MCP) → definição estática no registry + executor em `infrastructure/pg/tool_executors.py` (o registry e o `EXECUTORS` expõem pela mesma chave `tool.name`)
- Nova regra de autoria/validação → `core/domain/` (ex.: regra de validação de artefato/test)
- Nova dependência externa no core → definir/estender um **Port** em `core/ports/` + adapter em `infrastructure/` + wire em `composition.py`
- Nova tabela de agregado → modelo em `models/` + repository em `db/` + migration em `db/migrations/`
- Novo **flow** (workflow) → pack no cliente (`client/src/templates/flows/<slug>/` com `manifest.js` + `skills/` + `commands/`) registrado via `register_flow`; **não** exige código no servidor
- Nova regra declarativa de validação por kind → `artifact_kinds.rules` (`required_headings` / `required_metadata_keys`), sem código Python
- Novo comando de administração → sub-typer em `cli/<domínio>.py` + wire em `cli/main.py`
- Novo recurso exposto via MCP resources → `infrastructure/mcp_resources.py`

---

## Comunicação entre Componentes (mala prática ↔ boa prática, do artigo)

| Modo | Quando usar | Exemplo no projeto |
|---|---|---|
| Chamada direta | Interface para o mundo externo (API/view) | `mcp/server.py` → `ExecuteToolUseCase` |
| Via port (abstract class) | Componente core precisa de infra | Use cases → `RateLimiterPort`, `LoggerPort` |
| **Evitado:** eventos (blinker) | Não há necessidade de desacoplar eventos | — |

**Anti-deps proibidos:**
- Import de `db/repository` dentro de `mcp/` ou `cli/` (testado)
- Import de adapters em `core/` (testado)
- `core/domain` importando qualquer coisa com I/O (testado)
- DTOs: sempre via `Request`/`Response` — nunca exponha um objeto pydantic de `models/` (entidade de banco) diretamente como retorno de um use case.

---

## Testes

Foco por componente, seguindo o artigo:

1. **Testes de componente** exercitam a API pública (use cases contra adapters em memória) — o componente inteiro é a unidade. Evitar over-mocking das bordas.
2. **Testes de arquitetura** (`tests/architecture/test_imports.py`) automatizam as regras de import — o equivalente ao `pylint-forbidden-imports` do artigo, mas como teste pytest simples e sem linter extra.
3. **Testes de integração** cobrem a comunicação postgres real (`db/` + adapters pg), garantindo que os componentes conversam entre si ao rodar sob o `docker compose`.
4. **Stubs sobre mocks:** para os ports, preferimos stubs manuais simples (implementação mínima do Protocol) em vez de mocks framework-heavy — ver artigo "[beware of chicken testing](https://breadcrumbscollector.tech/beware-of-chicken-testing-or-mocks-overuse/)".

---

## Checklist antes de finalizar uma mudança no backend

- [ ] `core/` continua importando só de `core/domain` e `core/ports`
- [ ] Nenhuma entidade de banco vazou por um use case (troca por `Response`/DTO)
- [ ] Novo adapter implementado como Protocol + registrado no `composition.py`
- [ ] `pytest tests/architecture/ -q` passa
- [ ] Nenhum import circular novo (composition é o único módulo "importa tudo")
- [ ] Tool nova tem: definição no registry + executor + schema validado em entrada e saída