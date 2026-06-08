# OpenSddRag

**Spec-Driven Development (SDD) + Harness** — servidor MCP com memória semântica persistente e fluxo de trabalho estruturado para desenvolvimento de software disciplinado.

---

## O que é o OpenSddRag

O OpenSddRag entrega aos agentes de IA (como o Claude Code) uma **memória persistente** e um **fluxo de trabalho guiado por especificações**. Em vez de o agente trabalhar de forma improvisada, cada mudança passa por fases bem definidas: proposta → spec → design → tasks → implementação → verificação → archive.

### Dois pacotes independentes

| Pacote | Tecnologia | Função |
|---|---|---|
| `mcp-server/` | Python + PostgreSQL/pgvector | Servidor MCP central: armazena artefatos, traces e contexto de sessão |
| `client/` | Node.js | CLI que conecta qualquer projeto a um servidor MCP em execução |

### Conceito SDD (Spec-Driven Development)

Todo trabalho segue um ciclo de artefatos em ordem de dependência:

```
proposal → spec(s) → design → tasks → apply → verify → sync deltas → archive
```

Cada artefato vive no banco de dados com embedding vetorial, permitindo busca semântica sobre o histórico de decisões do projeto.

---

## Arquitetura

### Três camadas de memória

| Tabela | Tipo | Descrição |
|---|---|---|
| `artifacts` | Memória semântica | Propostas, specs, designs, tasks — cada uma com embedding `vector(384)` |
| `execution_traces` | Memória episódica | Log de ações do agente com embeddings para recall |
| `sessions` | Contexto de trabalho | IDs de artefatos ativos + JSON livre por projeto |
| `skills` | Templates SDD | Globais (`project_id IS NULL`) ou por projeto |
| `projects` | Registro multi-tenant | Projetos cadastrados no sistema |
| `artifact_relationships` | Grafo de dependências | Links entre artefatos (`depends_on`, `implements`, `relates_to`) |

Todos os vetores usam índices HNSW (`vector_cosine_ops`). Embeddings de 384 dimensões via `all-MiniLM-L6-v2`.

---

## Pré-requisitos

- **Docker** e **Docker Compose** (para banco de dados e servidor MCP em contêiner)
- **Python 3.11+** e **[uv](https://github.com/astral-sh/uv)** (para rodar o `mcp-server` localmente)
- **Node.js 18+** e **npm** (para o `client`)

---

## Início Rápido

O jeito mais simples de subir o banco e o servidor MCP juntos:

```bash
docker compose up -d
```

Isso inicia:
- **PostgreSQL/pgvector** na porta `54326` (mapeada do contêiner)
- **Servidor MCP** (modo SSE) na porta `8000`

Verifique que estão rodando:

```bash
curl http://localhost:8000/health
```

---

## Configuração de Ambiente

Antes de rodar o `mcp-server` localmente (fora do Docker), copie o arquivo de exemplo:

```bash
cp mcp-server/.env.example mcp-server/.env
```

Variáveis principais em `mcp-server/.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `postgresql://opensddrag:opensddrag@localhost:54326/opensddrag` | String de conexão com o banco |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Modelo de embedding (sentence-transformers) |
| `OPENSDDRAG_PROJECT` | `default` | Slug do projeto ativo |
| `AUTH_ENABLED` | `true` | Habilita autenticação no modo SSE |

---

## mcp-server (Python)

### Instalação

```bash
cd mcp-server

# Instala o pacote e dependências
uv pip install -e .

# Roda as migrations e faz seed das skills globais SDD
opensddrag init
```

### Execução local (modo stdio)

O Claude Code pode spawnar o servidor diretamente como processo filho:

```bash
opensddrag server start
```

### Execução como servidor HTTP (modo SSE)

Para uso remoto ou via Docker:

```bash
opensddrag server start --transport sse --port 8000
```

Endpoints disponíveis no modo SSE:
- `GET /health` — health check
- `GET /sse` — stream SSE para o cliente MCP
- `POST /messages/` — envio de mensagens MCP
- `GET /api/projects` — lista projetos (usado pelo client Node.js)
- `POST /api/projects` — cria projeto (usado pelo client Node.js)

### Testes

```bash
cd mcp-server

pytest                          # todos os testes
pytest tests/test_foo.py        # arquivo específico
pytest -k "test_nome"           # teste por nome
```

---

## client (Node.js)

O client conecta qualquer projeto de software a um servidor MCP em execução, instalando os arquivos necessários para o Claude Code se comunicar com o OpenSddRag.

### Instalação

```bash
cd client
npm install
```

### Conectar um projeto ao servidor MCP

Execute a partir da **raiz do projeto alvo** (não deste repositório):

```bash
node bin/opensddrag.js init [--server http://localhost:8000] [--project <slug>] [--yes]
```

Opções:
- `--server` — URL do servidor MCP (padrão: `http://localhost:8000`)
- `--project` — slug do projeto a registrar (padrão: nome do diretório)
- `--yes` — aceita todos os prompts automaticamente

### O que o `init` instala no projeto alvo

| Arquivo/Pasta | Descrição |
|---|---|
| `.mcp.json` | Configura o Claude Code para conectar ao servidor MCP via SSE |
| `.claude/commands/opsr/*.md` | Slash commands `/opsr:*` para o Claude Code |
| `.claude/skills/opensddrag-*/SKILL.md` | Skills do OpenSddRag para o Claude Code |
| `.agents/skills/opensddrag-*/SKILL.md` | Skills para outros agentes compatíveis |
| `CLAUDE.md` (seção adicionada) | Instrui o Claude Code sobre o projeto OpenSddRag |

### Verificar status da conexão

```bash
node bin/opensddrag.js status
```

---

## Transportes MCP

### stdio (uso local)

O Claude Code spawna o `opensddrag server start` como processo filho. A comunicação acontece via stdin/stdout. Ideal para desenvolvimento local onde o Claude Code e o servidor rodam na mesma máquina.

Configurado via `.mcp.json` no projeto alvo (gerado pelo `client init`):

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "stdio",
      "command": "opensddrag",
      "args": ["server", "start"]
    }
  }
}
```

### SSE (uso remoto ou Docker)

O servidor expõe endpoints HTTP. Adequado quando o servidor MCP roda em Docker, em outra máquina, ou deve ser compartilhado por múltiplos desenvolvedores.

Configurado via `.mcp.json` apontando para o endpoint SSE:

```json
{
  "mcpServers": {
    "opensddrag": {
      "type": "http",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Fluxo SDD

O fluxo completo de desenvolvimento orientado a spec:

| Fase | Artefato | Descrição |
|---|---|---|
| **propose** | `proposal.md` | Define o que e por que — problema, mudanças, capabilities afetadas |
| **spec** | `specs/<cap>/spec.md` | Define o que o sistema deve fazer — requisitos testáveis com cenários WHEN/THEN |
| **design** | `design.md` | Define como implementar — decisões técnicas, trade-offs, riscos |
| **tasks** | `tasks.md` | Lista de tarefas com checkboxes rastreáveis |
| **apply** | (código) | Implementação das tasks, marcando `[ ]` → `[x]` conforme avança |
| **verify** | (testes) | Valida que os cenários da spec foram atendidos |
| **sync deltas** | (delta specs) | Sincroniza specs modificadas de volta à base (`openspec/specs/`) |
| **archive** | (finalização) | Fecha a mudança, registra no histórico |

### Slash Commands

Instalados pelo `client init` em `.claude/commands/opsr/`:

| Comando | Fase | Descrição |
|---|---|---|
| `/opsr:propose` | Proposta | Cria a proposta e guia pela definição da mudança |
| `/opsr:spec` | Especificação | Gera as specs de capability baseadas na proposta |
| `/opsr:design` | Design | Cria o documento de design técnico |
| `/opsr:tasks` | Planejamento | Quebra o design em tasks implementáveis |
| `/opsr:apply` | Implementação | Implementa tasks sequencialmente, marcando progresso |
| `/opsr:verify` | Verificação | Valida os cenários das specs contra o código implementado |
| `/opsr:sync` | Sincronização | Mescla delta specs de volta às specs base |
| `/opsr:archive` | Arquivo | Finaliza e arquiva a mudança |
| `/opsr:explore` | Exploração | Investiga problemas antes de propor uma mudança |
| `/opsr:continue` | Continuação | Retoma uma mudança em andamento |
| `/opsr:status` | Status | Mostra o estado atual de todas as mudanças ativas |
| `/opsr:flow` | Fluxo | Guia interativo pelo próximo passo do fluxo SDD |
| `/opsr:search` | Busca | Busca semântica em artefatos e traces |

---

## Referência de Comandos CLI

Todos os comandos requerem que o banco de dados esteja acessível.

### Projetos

```bash
opensddrag project list              # lista todos os projetos
opensddrag project create <slug>     # cria um novo projeto
opensddrag project show <slug>       # exibe detalhes de um projeto
```

### Specs

```bash
opensddrag spec list                 # lista specs do projeto ativo
opensddrag spec create <nome>        # cria uma spec
opensddrag spec show <id>            # exibe uma spec específica
```

### Tasks

```bash
opensddrag task list                 # lista tasks do projeto ativo
opensddrag task create <descrição>   # cria uma task
opensddrag task show <id>            # exibe uma task específica
```

### Skills

```bash
opensddrag skill list                # lista skills disponíveis
opensddrag skill create <nome>       # cria uma skill
opensddrag skill suggest <query>     # sugere skills relevantes para uma query
```

### Busca Semântica

```bash
opensddrag search semantic "<query>" # busca artefatos por similaridade semântica
```

### Sessão e Workspace

```bash
opensddrag session show              # exibe o contexto de sessão do projeto ativo
opensddrag workspace init            # inicializa o workspace do projeto ativo
```

### Import OpenSpec

Importa artefatos de planejamento de um projeto OpenSpec para o OpenSddRag:

```bash
opensddrag import openspec /caminho/para/projeto              # importa todas as mudanças e specs globais
opensddrag import openspec /caminho/para/projeto --change add-auth   # importa apenas uma mudança
opensddrag import openspec /caminho/para/projeto --force             # re-importa e re-embeda existentes
opensddrag import openspec /caminho/para/projeto --project meu-slug  # especifica o projeto de destino
```

---

## Licença

Consulte o arquivo `LICENSE` na raiz do repositório.
