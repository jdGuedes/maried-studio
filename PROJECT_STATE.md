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

### AI-002 - BODY_DETAIL com ModelReference

- Status: `AUTO_VALIDATED`.
- Branch: `agent/STRUCTURAL-READY`.
- Implementado: `Generation.model_reference`, validações de payload por modo, persistência de `ModelReference` na geração e uso da instrução de modelo no `PromptEngine`.
- Contrato:
  - `STILL` rejeita cenário e modelo.
  - `BODY_DETAIL` exige modelo e rejeita cenário.
  - `INSTAGRAM` exige cenário e rejeita modelo.
  - `MODEL` exige modelo e rejeita cenário.
- Preservação: prompt `STILL` não foi alterado; regra `("EARRING", "BODY_DETAIL")` preserva fidelidade, escala, anatomia, composição e qualidade fotográfica, removendo apenas a descrição hardcoded da modelo para permitir `ModelReference`.
- Frontend: contrato TypeScript aceita `model_reference_id`; experiência final de seleção visual permanece em `FRONT-001`.
- Testes: cobertura de serializer, serviço, vínculo com `ModelReference`, listagem de `SceneTemplate` e regressão textual do prompt.

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

### AI-003 - Instagramável com SceneTemplate

- Status: `AUTO_VALIDATED`.
- Branch: `agent/STRUCTURAL-READY`.
- Implementado: `SceneTemplate` como cenário oficial de `INSTAGRAM` na V1, listagem pública autenticada somente para templates ativos de Instagramável, gestão estrutural via SuperAdmin e seed restrito a cenários Instagramáveis.
- APIs SuperAdmin:
  - `GET /api/superadmin/scene-templates/`
  - `POST /api/superadmin/scene-templates/`
  - `GET /api/superadmin/scene-templates/<id>/`
  - `PATCH /api/superadmin/scene-templates/<id>/`
  - `PUT /api/superadmin/scene-templates/<id>/`
- Segurança: endpoints SuperAdmin exigem `is_superuser`.
- Contrato: `SceneTemplate` fora de `INSTAGRAM` é rejeitado no SuperAdmin e não aparece na listagem pública.
- Seed: `seed_studio` não cria `SceneTemplate` para `MODEL`, `BODY_DETAIL` ou `STILL`.
- Pendência: biblioteca oficial de cenários e prompts finais dependem de validação humana de produto.

### AI-004 - MODEL / Na Modelo com ModelReference

- Status: `AUTO_VALIDATED`.
- Branch: `agent/STRUCTURAL-READY`.
- Implementado/validado: label `Na Modelo`, exigência de `model_reference_id`, rejeição de `scene_template_id`, vínculo da geração com `ModelReference`, instrução da `ModelReference` no `PromptEngine` e regras estruturais `MODEL` por categoria no seed.
- Créditos: segue regra V1 `1 geração = 1 crédito`.
- Pendência: enquadramento visual final corpo inteiro ou 3/4, poses, composição e legibilidade por categoria exigem validação humana de produto.

### FRONT-001 - Fluxos dos quatro modos

- Status: `AUTO_VALIDATED`.
- Branch: `agent/STRUCTURAL-READY`.
- Implementado: wizard de criação com labels oficiais, seleção condicional por modo, `ModelReference` para `BODY_DETAIL` e `MODEL`, `SceneTemplate` para `INSTAGRAM` e `STILL` sem seleção adicional.
- Contrato frontend:
  - `STILL`: envia `scene_template_id=null` e `model_reference_id=null`.
  - `BODY_DETAIL`: envia `model_reference_id`.
  - `MODEL`: envia `model_reference_id`.
  - `INSTAGRAM`: envia `scene_template_id`.
- Validação visual: `/criar` renderizou sem overlay em `http://localhost:3000`; interação de categoria funcionou.
- Pendência: fluxo autenticado com upload/geração real precisa validação humana com arquivo de teste.

### PromptEngine com quatro modos

O `PromptEngine` atual já contém os modos:

- `STILL`
- `BODY_DETAIL`
- `INSTAGRAM`
- `MODEL`

Observação:

Esses modos existem conceitualmente no motor, mas nem todos estão completos ou validados em produto.

### SceneTemplate compatível com Instagram

`SceneTemplate` está estruturado como cenário do modo `INSTAGRAM`.

Ainda falta definir biblioteca oficial, prompts finais, previews e fluxo completo no frontend, conforme validação humana de produto.

## TESTES DA CONSOLIDAÇÃO ESTRUTURAL

Última execução na branch `agent/STRUCTURAL-READY`:

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `python manage.py test apps.studio --keepdb`: passou, 15 testes.
- `python manage.py test apps.studio apps.superadmin --keepdb`: passou, 19 testes.
- `python manage.py test --keepdb`: passou, 40 testes.
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

- completar regras especializadas pendentes;
- calcular área corporal automaticamente por categoria.

### Instagramável

Planejado:

- exibir `INSTAGRAM` como Instagramável;
- definir cenários oficiais aprovados pelo produto;
- listar cenários ativos no frontend;
- validar visualmente antes de produção.

### Na Modelo

Planejado:

- exibir `MODEL` como Na Modelo;
- usar `ModelReference`;
- validar visualmente corpo inteiro ou 3/4 conforme legibilidade da peça;
- validar visualmente antes de produção.

### Frontend

Implementado estruturalmente:

- labels oficiais dos modos;
- seleção de modelo para Detalhe no Corpo;
- seleção de cenário para Instagramável;
- seleção de modelo para Na Modelo;
- Still sem seleção adicional;
- bloqueio de combinações inválidas.

Pendente:

- validação autenticada com upload e geração real;
- ajuste visual fino após aprovação humana.

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
