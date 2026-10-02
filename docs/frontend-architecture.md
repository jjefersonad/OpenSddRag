# Arquitetura do Frontend

Referência técnica da aplicação `frontend/` — React/Vite/TypeScript.
Para tokens e componentes visuais, consultar [`design_system/DESIGN_SYSTEM.md`](../design_system/DESIGN_SYSTEM.md).
Para comandos de build, portas e variáveis de ambiente, consultar [`CLAUDE.md`](../CLAUDE.md).

---

## Stack

| Tecnologia | Papel |
|---|---|
| React | UI framework |
| Vite |  Build tool e dev server |
| TypeScript | Tipagem estática |
| Tailwind CSS | Estilos via tokens |
| Axios | Clientes HTTP |
| Zustand | Gerenciamento de estado |
| React Router | Roteamento SPA |
| Socket.io-client | WebSocket |
| Headless UI | Componentes acessíveis sem estilo |

---

## Estrutura de Diretórios

```
frontend/src/
├── pages/           # Telas da aplicação (um arquivo por rota)
├── components/      # Componentes React organizados por domínio
│   ├── common/      # Componentes genéricos reutilizáveis (Button, Input, Modal, Badge)
│   ├── home/        # Componentes da tela inicial
│   ├── layout/      # Estrutura de página (Layout, AdminLayout, Sidebar, TopBar)
│   ├── logos/       # SVGs de logo como componentes React
│   └── ui/          # Primitivos de UI (Icon)
├── hooks/           # Custom hooks — wrappers sobre stores e lógica reutilizável
├── services/        # Clientes HTTP por domínio (funções puras, sem estado)
├── stores/          # Estado global (Zustand)
├── lib/             # Infraestrutura: clientes Axios, WebSocket, utilitários
├── types/           # Tipos TypeScript por domínio
├── tokens/          # Tokens de design espelhados do design_system
└── routes/          # Definição de rotas React Router
```

---

## Camadas e Responsabilidades

```
┌──────────────────────────────────────────────────────────┐
│  pages/          Telas — orquestram componentes e hooks  │
└───────────────────────────┬──────────────────────────────┘
                            │ usa
┌───────────────────────────▼──────────────────────────────┐
│  components/     Renderização — recebem props, sem fetch │
│  hooks/          Lógica reutilizável — wrappam stores    │
└──────────────┬──────────────────────┬────────────────────┘
               │ chama                │ lê/escreve
┌──────────────▼──────────┐  ┌────────▼───────────────────┐
│  services/              │  │  stores/                   │
│  HTTP por domínio       │  │  Estado global (Zustand)   │
└──────────────┬──────────┘  └────────────────────────────┘
               │ usa
┌──────────────▼──────────────────────────────────────────┐
│  lib/api.ts  lib/authApi.ts   lib/socket.ts             │
│  Infraestrutura HTTP e WebSocket                        │
└─────────────────────────────────────────────────────────┘
```

**Regra de dependência:** camadas superiores dependem das inferiores; nunca o contrário.
`pages` nunca importam de outros `pages`. `services` nunca importam de `stores` ou `hooks`.

**Onde colocar o quê:**
- Novo componente genérico → `components/common/`
- Novo componente específico de domínio → `components/<domínio>/`
- Nova chamada HTTP → `services/<domínio>.service.ts`
- Novo estado global → `stores/<domínio>.store.ts` + hook em `hooks/use<Domínio>.ts`

---

## Gerenciamento de Estado (Zustand)

### Stores existentes

| Store | Arquivo | Persiste? | Responsabilidade |
|---|---|---|---|
| `useAuthStore` | `stores/auth.store.ts` | Sim (localStorage) | Usuário autenticado, tokens JWT |

### Padrão: hook-over-store

Componentes nunca importam stores diretamente. Cada store tem um hook correspondente em `hooks/` que expõe a API pública:

```
useAuthStore (store)  →  useAuth (hook)  →  componentes
```

`useAuth` adiciona computed values como `isAdmin`, `isManager`, `hasPesquisaAccess` por cima dos dados brutos do store.

### Acesso fora do React tree

Interceptors Axios e código fora de componentes devem acessar o store via `.getState()`:

```ts
// correto — fora do React tree (ex: interceptor)
const token = useAuthStore.getState().token
useAuthStore.getState().logout()
```

---

## Clientes HTTP (Axios)

### `lib/api.ts`

- **Base URL:** `VITE_API_URL` (padrão: `http://localhost:8081/api/v1`)
- **Usado por:** `services/municipio.service.ts`, `services/pesquisa.service.ts`, `services/regiao.service.ts`
- **Interceptor de request:** injeta `Authorization: Bearer <token>` automaticamente
- **Auto-refresh JWT:** em resposta 401, tenta refresh via `useAuthStore.refreshAccessToken()`. Requisições concorrentes são enfileiradas e retomadas após o refresh. Se o refresh falhar → `logout()` + redirect para `/login`

### `lib/authApi.ts` — auth-service

- **Base URL:** `VITE_AUTH_API_URL` (padrão: `http://localhost:8090/api/v1`)
- **Usado por:** `stores/auth.store.ts` (login, logout, refresh-token)
- **Mesmo mecanismo de auto-refresh**, mas ignora URLs `/auth/refresh-token` e `/auth/login` para evitar loop infinito

### Adicionando um novo serviço de backend

Se um novo serviço (ex: research-service) precisar de cliente próprio, criar `lib/researchApi.ts` no mesmo padrão de `api.ts`, configurar `VITE_RESEARCH_API_URL` e adicionar o serviço correspondente em `services/`.

---

## Roteamento

Rotas definidas em `routes/index.tsx` com React Router v6.

### Tipos de rota

```tsx
// Pública
<Route path="/login" element={<LoginPage />} />

// Protegida por autenticação
<Route path="/territorios" element={
  <ProtectedRoute>
    <TerritoriosPage />
  </ProtectedRoute>
} />

// Protegida por permissão (role)
<Route path="/pesquisa" element={
  <ProtectedRoute>
    <PermissionRoute allowed={!!hasPesquisaAccess}>
      <PesquisaPage />
    </PermissionRoute>
  </ProtectedRoute>
} />

// Admin (autenticação + layout diferente)
<Route path="/admin/territorios" element={
  <ProtectedRoute>
    <AdminLayout>
      <TerritoriosPage />
    </AdminLayout>
  </ProtectedRoute>
} />
```

| Wrapper | Arquivo | Comportamento se não autorizado |
|---|---|---|
| `ProtectedRoute` | `components/ProtectedRoute.tsx` | Redireciona para `/login` |
| `PermissionRoute` | `components/PermissionRoute.tsx` | Renderiza fallback (sem redirect) |
| `AdminLayout` | `components/layout/AdminLayout.tsx` | Layout com sidebar admin |

Rotas `*` (not found) redirecionam para `/`.

---

## Autenticação e RBAC

### Fluxo JWT

```
1. Login    → POST /auth/login via authApi → access_token + refresh_token
2. Persist  → Zustand persist salva tokens no localStorage (chave: "auth-storage")
3. Request  → api.ts injeta Bearer token em cada chamada
4. Expirou  → Interceptor captura 401 → POST /auth/refresh-token → novo token
5. Falhou   → logout() → limpa store + localStorage → redirect /login
```

### Roles

Acessados exclusivamente via `useAuth()`:

```ts
const { isAdmin, isManager, hasPesquisaAccess } = useAuth()
```

| Computed | Roles que satisfazem |
|---|---|
| `isAdmin` | `admin` |

**Regra:** componentes nunca leem roles de `useAuthStore` diretamente — sempre via `useAuth()`.

---

## Integração com Design System

O `design_system/` é um app Vite separado que serve como **playground de referência** — não é importado como dependência pelo frontend.

O frontend consome o design system via espelhamento de tokens:

```
design_system/src/data.ts        ← fonte primária dos tokens
        ↕  (manter em sync manual)
frontend/src/tokens/colors.ts    ← espelho usado pelo frontend
frontend/tailwind.config.js      ← aplica os tokens via Tailwind
```

**Ao alterar ou adicioanr qualquer token de cor, atualizar AMBOS os arquivos.**

Para referência de componentes, padrões visuais e especificações de design, consultar [`./ui/AGENT_GUIDE.md`](./ui/AGENT_GUIDE.md).
