## Context

O OpenSddRag é uma ferramenta composta por dois pacotes independentes (`mcp-server/` em Python e `client/` em Node.js). Atualmente não existe nenhum `README.md` na raiz do repositório. Toda a documentação existente está espalhada no `CLAUDE.md` (voltado para o Claude Code, não para usuários finais) e nos arquivos internos do projeto.

Novos usuários e colaboradores precisam de um único ponto de entrada que explique como instalar, configurar e usar a ferramenta do início ao fim.

## Goals / Non-Goals

**Goals:**
- Criar um `README.md` na raiz do repositório com documentação completa de uso
- Cobrir instalação, configuração, comandos CLI, transportes MCP e fluxo SDD
- Ser acessível tanto para desenvolvedores que querem rodar localmente quanto para quem quer usar via Docker/SSE

**Non-Goals:**
- Documentação de API interna (funções, classes, módulos) — isso é responsabilidade de docstrings e comentários no código
- Guia de contribuição detalhado (pode ser um CONTRIBUTING.md separado no futuro)
- Documentação de deployment em produção além do docker compose básico

## Decisions

### Único arquivo README.md na raiz
**Decisão**: Um único `README.md` na raiz, sem sub-documentos separados por pacote.
**Rationale**: Mantém o ponto de entrada simples. A estrutura de seções com headers permite navegação via âncoras no GitHub. Documentação fragmentada aumenta a chance de desatualização.
**Alternativa considerada**: `mcp-server/README.md` e `client/README.md` separados — descartado porque aumenta a fricção para quem está explorando o projeto pela primeira vez.

### Idioma: Português
**Decisão**: README escrito em português, alinhado com o idioma do usuário e do contexto do projeto.
**Rationale**: O projeto é usado por uma equipe brasileira. README em português reduz a barreira de entrada para o público-alvo principal.

### Estrutura de seções
**Decisão**: Seguir a estrutura padrão de README de projetos técnicos:
1. Título e descrição curta
2. Visão geral e arquitetura
3. Pré-requisitos
4. Instalação rápida (docker compose)
5. mcp-server — setup e uso
6. client — setup e uso
7. Transportes MCP (stdio vs SSE)
8. Fluxo SDD e slash commands
9. Referência de comandos CLI

**Rationale**: Segue progressão natural do "o que é" → "como instalar" → "como usar" → "referência".

## Risks / Trade-offs

- **Risco de desatualização**: O README pode ficar desatualizado conforme o projeto evolui. → Mitigação: manter o README como parte do checklist de PR para mudanças que afetam CLI, comandos ou fluxo.
- **Duplicação com CLAUDE.md**: Parte da informação existente no `CLAUDE.md` será replicada no `README.md`. → Aceitável: são audiências diferentes (Claude Code vs usuário humano).

## Open Questions

- O README deve incluir capturas de tela ou exemplos de output de terminal? → Decisão: incluir blocos de código com exemplos de comandos, sem capturas de tela (evita manutenção de imagens).
