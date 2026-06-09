## 1. Improve CLI success output

- [ ] 1.1 In `client/src/commands/init.js`, replace the final two `console.log` lines with a richer success block that prints: the configured server URL, the project slug, and a numbered "next steps" list (open in Claude Code / OpenCode, run `/opsr:status`)
- [ ] 1.2 Verify that `opensddrag init --server <url> --project <slug> --yes` prints the server URL, slug, and next-steps hint in its output

## 2. Create client/README.md

- [ ] 2.1 Create `client/README.md` with: one-paragraph overview, prerequisites (Node.js 18+), installation steps (`npm install` inside `client/`), usage section covering `init` (with flag reference: `--server`, `--project`, `--yes`, `--tools`, `--api-key`) and `status` commands, and a troubleshooting section for "Cannot reach server" error
- [ ] 2.2 Ensure `client/README.md` is self-contained — a user reading only that file can install and connect without reading the root README

## 3. Add Quick Install section to root README.md

- [ ] 3.1 Add a new section `## Início Rápido — Conectando ao Servidor Hospedado` to root `README.md` immediately after the "Pré-requisitos" section
- [ ] 3.2 Section must include: prerequisites note (Node.js 18+), clone/download step, `npm install` command (run inside `client/`), and `node bin/opensddrag.js init --server <URL_DO_SERVIDOR> --project <seu-projeto>` with a note that `<URL_DO_SERVIDOR>` is the hosted Portainer URL provided by the maintainer
- [ ] 3.3 Add a "Verificando a conexão" subsection showing `node bin/opensddrag.js status` so users can confirm setup worked
