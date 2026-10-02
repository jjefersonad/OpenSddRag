# Testes E2E — Playwright + Page Object Model

Guia de processo para escrever, rodar e manter os testes end-to-end do frontend.

---

## Pré-requisitos

| Requisito | Detalhes |
|-----------|----------|
| Node.js ≥ 20 | Instalado com `nvm` ou via pacote |
| `auth-service` rodando | `http://localhost:8080` |
| `frontend` rodando | `http://localhost:5173` (dev) ou `npm run build && npm run preview` |
| `research-service` | `http://localhost:8082` — necessário para testes do mapa exploratório |
| Arquivo `e2e/.env.test` | Copiado de `e2e/.env.test.example` e preenchido |

### Configurar credenciais

```bash
cp frontend/e2e/.env.test.example frontend/e2e/.env.test
# Editar o arquivo com credenciais reais de teste
```

Variáveis obrigatórias:

```env
E2E_BASE_URL=http://localhost:5173
E2E_ADMIN_EMAIL=admin@example.com
E2E_ADMIN_PASSWORD=senha-do-admin
E2E_USER_EMAIL=usuario@example.com
E2E_USER_PASSWORD=senha-do-usuario
```

---

## Como rodar os testes

```bash
cd frontend

# Rodar todos os testes em modo headless
npm run test:e2e

# Abrir a interface visual do Playwright (modo interativo)
npm run test:e2e:ui

# Rodar apenas um arquivo de spec
npm run test:e2e -- auth.spec.ts

# Ver o relatório HTML após a execução
npx playwright show-report
```

O relatório fica em `frontend/playwright-report/` (ignorado pelo git).

---

## Estrutura de diretórios

```
frontend/e2e/
├── .env.test              # (gitignored) credenciais de teste
├── .env.test.example      # template público — comitar alterações aqui
├── .auth/
│   └── admin.json         # (gitignored) storageState salvo pelo setup
├── fixtures/
│   ├── auth.setup.ts      # projeto "setup": login via UI → salva storageState
│   └── municipios.geojson.ts  # fixture GeoJSON mínimo para testes do mapa
├── page-objects/
│   ├── base.page.ts       # BasePage — helpers compartilhados
│   ├── login.page.ts      # LoginPage
│   ├── home.page.ts       # HomePage
│   ├── tematicas.page.ts  # TematicasPage
│   ├── territorios.page.ts # TerritoriosPage
│   ├── pesquisas.page.ts  # PesquisasPage
│   ├── exploratory-map.page.ts # ExploratoryMapPage
│   └── admin.page.ts      # AdminPage
└── tests/
    ├── auth.spec.ts
    ├── home.spec.ts
    ├── tematicas.spec.ts
    ├── territorios.spec.ts
    ├── pesquisas.spec.ts
    ├── exploratory-map.spec.ts
    └── admin.spec.ts
```

---

## Convenções de nomenclatura

| Artefato | Padrão | Exemplo |
|----------|--------|---------|
| Arquivo de Page Object | `<dominio>.page.ts` | `tematicas.page.ts` |
| Classe de Page Object | `<Dominio>Page` | `TematicasPage` |
| Arquivo de spec | `<dominio>.spec.ts` | `tematicas.spec.ts` |
| Atributo `data-testid` | `kebab-case` descritivo | `btn-criar-tema`, `login-email` |
| Prefixos de testid | `btn-` (botão), `tab-` (aba), `sidebar-item-`, `nav-item-` | |

---

## Como criar um Page Object

Crie um arquivo em `e2e/page-objects/<dominio>.page.ts`:

```typescript
import { BasePage } from './base.page'

export class MinhaPage extends BasePage {
  // Declare locators como propriedades usando getByTestId
  readonly meuBotao = this.getByTestId('btn-minha-acao')
  readonly meuModal = this.getByTestId('meu-modal')

  // Método de navegação
  async abrirModal(): Promise<void> {
    await this.meuBotao.click()
    await this.meuModal.waitFor({ state: 'visible' })
  }

  // Método de asserção
  async assertConteudoVisivel(texto: string): Promise<void> {
    await this.page.getByText(texto).waitFor({ state: 'visible' })
  }
}
```

**Regras:**
- Sempre estender `BasePage`
- Locators simples → propriedades readonly (`this.getByTestId(...)`)
- Locators dinâmicos → calcular no método (`this.getByTestId(`item-${id}`)`)
- Métodos retornam `Promise<void>` e aguardam estabilidade da rede
- Nunca usar `page.waitForTimeout()` — prefira `waitFor({ state: 'visible' })`

### Adicionar `data-testid` ao componente

Todo elemento interagido por testes deve ter `data-testid`:

```tsx
// Botão
<Button data-testid="btn-criar-recurso" onClick={handleCreate}>
  Criar
</Button>

// Input
<input data-testid="recurso-nome" value={form.nome} onChange={...} />

// Container de lista
<div data-testid="recursos-list">
  {items.map(...)}
</div>
```

---

## Template de teste (`.spec.ts`)

```typescript
import { test, expect } from '@playwright/test'
import { MinhaPage } from '../page-objects/minha.page'

// Testes que precisam de sessão autenticada usam o storageState padrão
// configurado em playwright.config.ts (via auth.setup.ts)
test.describe('Minha Feature', () => {
  test('deve fazer X com sucesso', async ({ page }) => {
    const minha = new MinhaPage(page)
    await minha.goto('/minha-rota')
    await minha.abrirModal()
    await expect(minha.meuModal).toBeVisible()
  })
})

// Testes SEM autenticação: usar browser.newContext sem storageState
test('acesso não autenticado redireciona para login', async ({ browser }) => {
  const context = await browser.newContext({ storageState: undefined })
  const page = await context.newPage()
  await page.goto('/rota-protegida')
  await expect(page).toHaveURL(/\/login/)
  await context.close()
})
```

---

## Checklist de PR

Para todo PR que altera o frontend, verificar antes de solicitar review:

- [ ] Novos elementos interativos têm `data-testid` no formato `kebab-case`
- [ ] Se adicionou uma nova rota/página: criou ou atualizou o Page Object correspondente
- [ ] Se adicionou uma nova página: criou pelo menos um smoke test em `e2e/tests/`
- [ ] Os testes existentes continuam passando (`npm run test:e2e`)
- [ ] `data-testid` adicionados são únicos na página (evitar duplicatas no mesmo contexto)
