## 1. Estrutura e Visão Geral

- [x] 1.1 Criar o arquivo `README.md` na raiz do repositório com título, badges básicos e descrição de uma linha do projeto
- [x] 1.2 Escrever a seção "O que é o OpenSddRag" com visão geral, os dois pacotes principais e o conceito de SDD
- [x] 1.3 Escrever a seção "Arquitetura" resumindo as três camadas de memória (artifacts, execution_traces, sessions) e o schema de banco de dados

## 2. Instalação e Configuração

- [x] 2.1 Escrever a seção "Pré-requisitos" listando Docker, Python 3.11+, uv, e Node.js 18+
- [x] 2.2 Escrever a seção "Início Rápido" com `docker compose up -d` e as portas padrão (MCP em 8000, PostgreSQL em 54326)
- [x] 2.3 Documentar o passo de cópia do `.env.example` para `.env` e as variáveis de ambiente principais (`DATABASE_URL`, `EMBEDDING_MODEL`, `OPENSDDRAG_PROJECT`)

## 3. mcp-server (Python)

- [x] 3.1 Documentar instalação: `uv pip install -e .` e `opensddrag init` (migrations + seed de skills)
- [x] 3.2 Documentar execução local em modo stdio: `opensddrag server start`
- [x] 3.3 Documentar execução em modo HTTP/SSE: `opensddrag server start --transport sse --port 8000`
- [x] 3.4 Documentar execução dos testes: `pytest` e variações com filtro de arquivo/nome

## 4. client (Node.js)

- [x] 4.1 Documentar instalação: `npm install` no diretório `client/`
- [x] 4.2 Documentar o comando `opensddrag init` com opções `--server`, `--project` e `--yes`
- [x] 4.3 Listar o que o `init` instala no projeto alvo: `.mcp.json`, comandos slash em `.claude/commands/opsr/`, skills e seção no `CLAUDE.md`
- [x] 4.4 Documentar o comando `opensddrag status`

## 5. Transportes MCP

- [x] 5.1 Explicar o transporte stdio: quando usar, como o Claude Code spawna o processo
- [x] 5.2 Explicar o transporte SSE: quando usar (Docker/remoto), endpoints `/sse`, `/messages/`, `/health`

## 6. Comandos CLI — Referência

- [x] 6.1 Listar e descrever todos os subcomandos de `project` (list, create, show)
- [x] 6.2 Listar e descrever todos os subcomandos de `spec`, `task`, `skill`
- [x] 6.3 Listar e descrever `search semantic`, `session show`, `workspace init`
- [x] 6.4 Documentar o comando `import openspec` com todas as opções (`--change`, `--force`, `--project`)

## 7. Fluxo SDD e Slash Commands

- [x] 7.1 Escrever a seção do fluxo SDD descrevendo cada fase: `proposal → spec(s) → design → tasks → apply → verify → sync deltas → archive`
- [x] 7.2 Listar todos os slash commands (`/opsr:propose`, `/opsr:spec`, `/opsr:design`, `/opsr:tasks`, `/opsr:apply`, `/opsr:verify`, `/opsr:sync`, `/opsr:archive`, `/opsr:explore`, `/opsr:continue`, `/opsr:status`, `/opsr:flow`, `/opsr:search`) com descrição de cada um

## 8. Revisão Final

- [x] 8.1 Revisar o README completo verificando links internos, formatação de blocos de código e consistência de termos
- [x] 8.2 Verificar que todos os requisitos da spec `readme-documentation` estão cobertos no documento final
