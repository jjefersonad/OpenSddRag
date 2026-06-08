## ADDED Requirements

### Requirement: propose command instructs agent not to replace TODO placeholders
O comando `/opsr:propose` SHALL incluir, em cada etapa de criação de artefato esboço (spec e design), uma instrução explícita e em negrito proibindo o agente de substituir os marcadores `[TODO]` por conteúdo gerado. Os marcadores devem ser copiados literalmente para o banco de dados exatamente como estão no template.

#### Scenario: Agente copia placeholder literalmente ao criar spec draft
- **WHEN** o agente executa o Step 5 do `/opsr:propose` e chama `create_artifact` para uma capability
- **THEN** o conteúdo salvo no banco contém a string literal `[TODO: Describe requirement using SHALL/MUST language]` (ou similar) sem substituição
- **THEN** o conteúdo salvo NO contém requisitos específicos do domínio (como regras JWT, schemas de banco, tokens de autenticação) não mencionados pelo usuário na proposta

#### Scenario: Agente copia placeholder literalmente ao criar design draft
- **WHEN** o agente executa o Step 6 do `/opsr:propose` e chama `create_artifact` para o design skeleton
- **THEN** o conteúdo salvo contém seções com marcadores `[TODO]` literais
- **THEN** as seções de Decisions, Risks e Architecture não contêm escolhas técnicas específicas geradas pelo agente

### Requirement: instrução de não preenchimento deve ser visualmente destacada
A instrução de não substituir placeholders SHALL ser destacada com negrito ou bloco de aviso (ex.: `**IMPORTANT**`) dentro do template do comando, de modo que o agente não possa ignorá-la.

#### Scenario: Instrução destacada no Step 5
- **WHEN** o agente lê o Step 5 do template do `/opsr:propose`
- **THEN** encontra uma linha do tipo `**IMPORTANT: copy the template content VERBATIM — do NOT replace [TODO] markers with generated content**` imediatamente antes do bloco de código `create_artifact`

#### Scenario: Instrução destacada no Step 6
- **WHEN** o agente lê o Step 6 do template do `/opsr:propose`
- **THEN** encontra uma linha similar proibindo o preenchimento do design skeleton
