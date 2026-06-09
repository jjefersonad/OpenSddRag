## 1. Translate README.md

- [x] 1.1 Translate the "O que é o OpenSddRag" section to English ("What is OpenSddRag")
- [x] 1.2 Translate the architecture overview table and artifact lifecycle description
- [x] 1.3 Translate the "Três camadas de memória" section ("Three Memory Layers")
- [x] 1.4 Translate the "Pré-requisitos" and "Início Rápido" sections ("Prerequisites" and "Quick Start")
- [x] 1.5 Translate the "Configuração de Ambiente" section ("Environment Configuration")
- [x] 1.6 Translate the "mcp-server" setup, run, and test sections
- [x] 1.7 Translate the "client" setup and usage sections
- [x] 1.8 Translate the "Fluxo SDD" and slash-command reference sections
- [x] 1.9 Review the full translated README for accuracy and consistency with the codebase

## 2. Translate SQL Migration Comments

- [x] 2.1 Translate Portuguese block comments in `mcp-server/src/opensddrag/db/migrations/001_initial.sql` to English (section headers only — no schema changes)

## 3. Verify Other Documentation

- [x] 3.1 Read `docs/authorization.md` and confirm it is entirely in English (translate any Portuguese passages if found)
- [x] 3.2 Read `client/README.md` and confirm it is entirely in English (translate any Portuguese passages if found)
- [x] 3.3 Read `client/CLAUDE.md` and confirm it is entirely in English (translate any Portuguese passages if found)

## 4. Document the Language Convention

- [x] 4.1 Append a "Language Convention" section to `CLAUDE.md` stating that all project-level text (source code, docs, comments) must be in English, and that database-persisted content (artifacts, traces, skills) is language-agnostic and must remain as written by the user
