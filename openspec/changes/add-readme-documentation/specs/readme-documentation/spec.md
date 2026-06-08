## ADDED Requirements

### Requirement: README covers project overview
O README.md SHALL incluir uma seção de visão geral descrevendo o que é o OpenSddRag, qual problema resolve e quais são os dois pacotes principais (`mcp-server/` e `client/`).

#### Scenario: Usuário entende o propósito ao ler o topo do README
- **WHEN** um novo usuário abre o README.md
- **THEN** encontra em menos de 30 linhas uma descrição clara do propósito da ferramenta, dos dois pacotes e do fluxo SDD básico

### Requirement: README covers installation and prerequisites
O README.md SHALL listar todos os pré-requisitos (Docker, Python, uv, Node.js) e os passos completos de instalação para ambos os pacotes.

#### Scenario: Usuário instala o mcp-server do zero
- **WHEN** o usuário segue a seção de instalação do mcp-server
- **THEN** consegue executar `opensddrag server start` sem erros após copiar o `.env.example` e rodar as migrações

#### Scenario: Usuário instala o client do zero
- **WHEN** o usuário segue a seção de instalação do client
- **THEN** consegue executar `opensddrag init` no projeto alvo sem erros após `npm install`

### Requirement: README covers database and infrastructure setup
O README.md SHALL documentar como iniciar o banco de dados via `docker compose up -d`, a porta padrão (`54326`), e como configurar variáveis de ambiente.

#### Scenario: Banco de dados sobe corretamente
- **WHEN** o usuário executa `docker compose up -d` após ler o README
- **THEN** o banco pgvector/pg16 está acessível em `localhost:54326`

### Requirement: README covers CLI commands
O README.md SHALL listar todos os comandos CLI do `opensddrag` com descrição curta de cada um, agrupados por categoria (project, spec, task, skill, search, session, workspace, import).

#### Scenario: Usuário encontra o comando correto
- **WHEN** o usuário precisa listar projetos existentes
- **THEN** encontra no README o comando `opensddrag project list` com descrição clara

### Requirement: README covers MCP transport modes
O README.md SHALL explicar os dois modos de transporte MCP (stdio e SSE) e quando usar cada um.

#### Scenario: Usuário entende quando usar SSE vs stdio
- **WHEN** o usuário lê a seção de transportes MCP
- **THEN** compreende que stdio é para uso local pelo Claude Code e SSE é para uso remoto/Docker

### Requirement: README covers SDD workflow
O README.md SHALL descrever o fluxo completo de desenvolvimento orientado a spec: `proposal → spec(s) → design → tasks → apply → verify → sync → archive`, com descrição curta de cada fase.

#### Scenario: Usuário entende a sequência de comandos SDD
- **WHEN** o usuário lê a seção de fluxo SDD
- **THEN** sabe que deve começar com `/opsr:propose` e terminar com `/opsr:archive`, e entende o que cada passo produz

### Requirement: README covers client slash commands
O README.md SHALL listar os slash commands instalados pelo client (`/opsr:propose`, `/opsr:spec`, `/opsr:design`, `/opsr:tasks`, `/opsr:apply`, `/opsr:verify`, `/opsr:sync`, `/opsr:archive`, `/opsr:explore`, `/opsr:continue`, `/opsr:status`, `/opsr:flow`, `/opsr:search`) com descrição de cada um.

#### Scenario: Usuário sabe qual slash command usar em cada fase
- **WHEN** o usuário está na fase de design
- **THEN** encontra no README que deve usar `/opsr:design` e o que esse comando faz
