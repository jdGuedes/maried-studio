# PROJECT_STATE.md - MARIED STUDIO

Estado do projeto para orientar o Codex e evitar confusão entre o que já está validado, implementado, em implementação e planejado.

## VALIDADO

### STILL

- Modo interno: `STILL`.
- Nome exibido: Still.
- Prompt validado.
- Fluxo conceitualmente validado.
- Não requer escolha adicional.
- Deve preservar fundo branco, fidelidade da peça e ausência de modelo/cenário.

Regra:

```text
Não reescrever, resumir ou otimizar o prompt Still sem autorização explícita.
```

### BODY_DETAIL para EARRING

- Modo interno: `BODY_DETAIL`.
- Nome exibido: Detalhe no Corpo.
- Regra especializada validada: `("EARRING", "BODY_DETAIL")`.
- Aplicação correta em orelha/lateral do rosto.
- Escala real e anatomia correta são requisitos validados.

Regra:

```text
Não reescrever, resumir ou otimizar EARRING + BODY_DETAIL sem autorização explícita.
```

## IMPLEMENTADO

### FOUNDATION-001 - Perfil e shell

- Status: `AUTO_VALIDATED`.
- Branch consolidada: `agent/STRUCTURAL-READY`.
- Implementado: `ProfileProvider`, `CreditWalletProvider`, `AppShell`, `DashboardHome`, `/api/accounts/me/` e carteira real.
- Segurança: perfil exige autenticação; PATCH comum não promove `is_superuser`; e-mail permanece somente leitura.
- Pendências: rotas comerciais futuras para Créditos e Minhas Criações.

### FOUNDATION-002 - Migration do UserManager

- Status: `AUTO_VALIDATED`.
- Branch consolidada: `agent/STRUCTURAL-READY`.
- Commit de origem: `40a538f chore: register accounts manager migration`.
- Implementado: `apps/accounts/migrations/0002_alter_user_managers.py`.
- Resultado: `makemigrations --check --dry-run` não detecta pendências.

### BILLING-001 - Plan e Subscription

- Status: `AUTO_VALIDATED`.
- Branch consolidada: `agent/STRUCTURAL-READY`.
- Implementado: `Plan`, `Subscription`, `BillingCycle.MONTHLY`, status de assinatura, snapshots comerciais, admin e testes.

### BILLING-002 - SubscriptionService

- Status: `AUTO_VALIDATED`.
- Branch consolidada: `agent/STRUCTURAL-READY`.
- Commit de origem: `f339059 feat: implement BILLING-002 subscription service`.
- Implementado: `SubscriptionService.activate(...)`, `renew_current_cycle(...)`, snapshots, cálculo mensal, atomicidade e integração com `CreditService`.
- Créditos: concessão e renovação passam por `CreditService`; créditos avulsos permanecem na renovação.

### AI-001 - ModelReference

- Status: `AUTO_VALIDATED`.
- Branch consolidada: `agent/STRUCTURAL-READY`.
- Commit de origem: `19a2ca8 feat: implement AI-001 model reference`.
- Implementado: model, admin, serializer, endpoint autenticado, seed/data migration e testes.
- Uso: catálogo global controlado para `BODY_DETAIL` e `MODEL`.

### ADMIN-001 - SuperAdmin Foundation

- Status: `AUTO_VALIDATED`.
- Branch: `agent/STRUCTURAL-READY`.
- Implementado: app `apps.superadmin`, endpoint de resumo, listagens globais e ajuste administrativo de crédito.
- APIs:
  - `GET /api/superadmin/summary/`
  - `GET /api/superadmin/organizations/`
  - `GET /api/superadmin/accounts/`
  - `GET /api/superadmin/plans/`
  - `GET /api/superadmin/subscriptions/`
  - `GET /api/superadmin/credit-wallets/`
  - `GET /api/superadmin/generations/`
  - `POST /api/superadmin/credit-adjustments/`
- Segurança: endpoints exigem `is_superuser`; usuário comum recebe 403.
- Créditos: ajuste usa `CreditService.adjust_credits`, impede saldo negativo e registra `CreditTransaction` + `AuditLog`.
- Testes: cobertura de acesso SuperAdmin, 403 para usuário comum, listagens, ajuste e rejeição de saldo negativo.

### PromptEngine com quatro modos

O `PromptEngine` atual já contém os modos:

- `STILL`
- `BODY_DETAIL`
- `INSTAGRAM`
- `MODEL`

Observação:

Esses modos existem conceitualmente no motor, mas nem todos estão completos ou validados em produto.

### SceneTemplate compatível com Instagram

`SceneTemplate` já é compatível com a ideia de cenários para o modo `INSTAGRAM`.

Ainda falta estruturar cadastro, biblioteca oficial e fluxo completo no frontend, conforme o estado real do código.

## TESTES DA CONSOLIDAÇÃO ESTRUTURAL

Última execução na branch `agent/STRUCTURAL-READY`:

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `python manage.py test apps.superadmin --keepdb`: passou, 5 testes.
- `python manage.py test --keepdb`: passou, 22 testes.
- `npm run lint`: passou.
- `npm run build`: passou.

## EM IMPLEMENTAÇÃO

### Reorganização oficial dos modos

Definição de produto aprovada:

| Interno | Exibição | Seleção |
| --- | --- | --- |
| `STILL` | Still | Nenhuma |
| `BODY_DETAIL` | Detalhe no Corpo | Modelo |
| `INSTAGRAM` | Instagramável | Cenário |
| `MODEL` | Na Modelo | Modelo |

### Documentação operacional para Codex

Este pacote documental define:

- PRD;
- SPEC;
- PLAN;
- ADR;
- AGENTS;
- PROJECT_STATE.

## PLANEJADO

### BODY_DETAIL para todas as categorias

Criar ou completar regras especializadas:

| Categoria | Área corporal |
| --- | --- |
| `EARRING` | orelha/lateral do rosto |
| `NECKLACE` | pescoço/colo |
| `RING` | mão/dedos |
| `BRACELET` | pulso/braço |
| `ANKLET` | tornozelo/pé/perna |

Mudança planejada:

- remover escolha de direção visual no `BODY_DETAIL`;
- adicionar escolha de `ModelReference`;
- calcular área corporal automaticamente por categoria.

### Instagramável

Planejado:

- exibir `INSTAGRAM` como Instagramável;
- usar `SceneTemplate`;
- permitir cenários cadastráveis pelo SuperAdmin;
- listar cenários ativos no frontend;
- validar visualmente antes de produção.

### Na Modelo

Planejado:

- exibir `MODEL` como Na Modelo;
- usar `ModelReference`;
- gerar corpo inteiro ou 3/4 conforme legibilidade da peça;
- criar regras por categoria;
- validar visualmente antes de produção.

### Frontend

Planejado:

- labels oficiais dos modos;
- seleção de modelo para Detalhe no Corpo;
- seleção de cenário para Instagramável;
- seleção de modelo para Na Modelo;
- Still sem seleção adicional;
- bloqueio de combinações inválidas.

### Créditos

Regra V1 planejada e aprovada:

```text
1 geração = 1 crédito
```

Aplica-se a todos os modos.

### Testes e validação

Planejado:

- testes de payload por modo;
- testes de consumo de crédito;
- testes de mapeamento corporal;
- testes de regressão dos prompts validados;
- validação visual humana antes de produção.

## ESTRATÉGIA MULTIAGENTE

Status: **APROVADA NA DOCUMENTAÇÃO**.

O projeto admite múltiplos agentes independentes, mas execução paralela exige:
- task file criado;
- status `READY`;
- dependências concluídas;
- ownership definido;
- shared files identificados;
- lock/coordenação quando necessário.

Workstreams aprovados:
- FOUNDATION
- BILLING
- BODY_DETAIL
- INSTAGRAMABLE
- ON_MODEL
- FRONTEND_INTEGRATION
- SUPERADMIN
- TESTS_QA

Dependências principais:
- `ModelReference` bloqueia integração de BODY_DETAIL e MODEL.
- Instagramável usa SceneTemplate e pode avançar independentemente quando não houver conflito de arquivos.

Estado operacional:
A estratégia está documentada. A execução paralela só deve começar quando task files e locks aplicáveis estiverem definidos.
