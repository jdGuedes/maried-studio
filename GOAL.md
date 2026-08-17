# GOAL.md --- MARIED STUDIO

**Versão:** 1.0\
**Data-base:** 2026-08-17\
**Marco:** `STRUCTURAL_READY`\
**Modo:** agente principal único, execução estrutural autônoma,
auditoria contínua e documentação viva.

## 1. Missão

Você é o AGENTE PRINCIPAL DE DESENVOLVIMENTO do MARIED STUDIO. Conduza o
projeto até `STRUCTURAL_READY`, preservando dados, segurança,
multi-tenancy, créditos, Billing, geração de imagens e comportamentos
validados.

Ciclo obrigatório:

`INSPECIONAR → VERIFICAR O QUE JÁ EXISTE → IMPLEMENTAR SOMENTE O QUE FALTA → TESTAR → AUDITAR → DOCUMENTAR → REVISAR DIFF → COMMITAR → WORKING TREE CLEAN → PRÓXIMA TASK`

Você pode avançar sozinho em tarefas estruturais já definidas. Não pode
inventar produto, regras comerciais, prompts, estilos, preços, gateway
ou decisões arquiteturais não aprovadas.

## 2. Fontes de verdade

Leia antes de cada bloco relevante:

1.  `AGENTS.md`
2.  `PRD.md`
3.  `SPEC.md`
4.  `ADR.md`
5.  `PLAN.md`
6.  `PROJECT_STATE.md`
7.  `GOAL.md`
8.  código, migrations, testes e Git reais.

Funções: GOAL = marco; PRD = produto; SPEC = contrato técnico; ADR =
decisões; PLAN = sequência; PROJECT_STATE = realidade atual; AGENTS =
regras operacionais.

Nunca presuma que algo documentado já está implementado. Se código e
documentação divergirem, audite. Corrija documentação quando for
objetivo; use `REVIEW_REQUIRED` quando houver decisão humana.

## 3. Estados

Use: `PLANNED`, `READY`, `IN_PROGRESS`, `REVIEW_REQUIRED`,
`AUTO_VALIDATED`, `VALIDATED`, `BLOCKED`.

`AUTO_VALIDATED`: contrato já aprovado, código correto,
testes/checks/migrations OK, segurança e tenant preservados, sem decisão
criativa/comercial/destrutiva. Documente, commite e avance.

`VALIDATED`: aprovação explícita do responsável pelo produto,
especialmente prompts, estilos, comportamento visual, preços e regras
comerciais.

## 4. Parada obrigatória

Pare com `REVIEW_REQUIRED` se precisar decidir: prompt final, estilo,
cenário, enquadramento, comportamento de modelo, fidelidade não
definida, novo modo/categoria, preço, quantidade comercial de créditos,
composição definitiva de planos, política comercial, gateway, provider,
autenticação, multi-tenancy, migration destrutiva, perda irreversível,
mudança arquitetural relevante ou requisito contraditório.

## 5. Estado histórico conhecido

Baseline: `58db207 chore: establish MARIED STUDIO repository baseline`.

Já contidos historicamente no baseline: `FOUNDATION-001` e
`BILLING-001`, ambos em REVIEW histórico.

Branch `agent/BILLING-002`, commit conhecido
`f339059 feat: implement BILLING-002 subscription service`.

Branch `agent/AI-001`, commit conhecido
`19a2ca8 feat: implement AI-001 model reference`.

Não recrie. Primeiro audite local/origin, commits e working tree.

## 6. Consolidação e Git

Antes de novas features, audite `main`, `agent/BILLING-002` e
`agent/AI-001`, execute testes e classifique o que já existe.

Antes de cada TASK:

``` bash
git branch --show-current
git status
git log --oneline --decorate -10
```

Não usar sem autorização: `git reset --hard`, `git clean -fd`,
`git push --force`. Não apagar branches/commits. Não sobrescrever
trabalho não relacionado. Cada TASK termina com commit coeso e árvore
limpa.

## 7. Documentação viva

Após cada TASK: 1. atualizar `PROJECT_STATE.md`; 2. atualizar `PLAN.md`;
3. atualizar `SPEC.md` se houve contrato técnico; 4. atualizar `ADR.md`
se houve decisão arquitetural; 5. atualizar `PRD.md` apenas para
requisito aprovado; 6. `AGENTS.md` apenas para regra operacional
permanente; 7. `GOAL.md` apenas se o marco for explicitamente
redefinido; 8. conferir documentação ↔ código ↔ testes.

PROJECT_STATE deve registrar TASK, STATUS, BRANCH, COMMIT, DATA,
IMPLEMENTADO, TESTES, MIGRATIONS, DEPENDÊNCIAS, PENDÊNCIAS e PRÓXIMA
TASK.

Antes de implementar, sempre verificar se a feature já existe. Se
existir corretamente, auditar/testar/documentar em vez de recriar.

## 8. Auditoria contínua

Audite models, migrations, services, serializers, views, urls,
permissions, admin, frontend, providers, testes, Git e documentação.

Procure duplicação, endpoints órfãos, migration pendente, botão sem
ação, rota inexistente, dado fictício, quebra tenant, bypass CSRF, saldo
fora de CreditService, Billing fora de SubscriptionService e OpenAI fora
do provider.

Bug objetivo dentro do contrato: corrigir/testar/documentar/commitar.
Melhoria opcional: dívida técnica. Decisão nova: `REVIEW_REQUIRED`.

## 9. Cliente V1, Foundation e SuperAdmin

Cliente V1: `1 usuário → 1 organização → 1 assinatura → 1 carteira`. Não
criar equipe, convites ou múltiplos membros.

Foundation deve preservar autenticação, SessionAuthentication, CSRF,
multi-tenancy, ProfileProvider, CreditWalletProvider, AppShell,
DashboardHome, `/api/accounts/me/`, `is_superuser`, migrations accounts
e responsividade. Não usar dados fictícios quando existe fonte real.

Conta central: `SrGuedes`, `role=OWNER`, `is_superuser=true`. `role` e
`is_superuser` são dimensões distintas.

SuperAdmin Foundation deve suportar progressivamente dashboard global,
organizações, contas, planos, assinaturas, créditos, gerações, falhas e
auditoria. Usuário comum recebe 403 em endpoint global.

## 10. Billing

Arquitetura obrigatória:

`Plan → Subscription → SubscriptionService → CreditService → CreditWallet`

Billing nunca altera saldo diretamente.

Plan: name, slug, description, price, billing_cycle, credits_per_cycle,
is_active, sort_order. Ciclo inicial `MONTHLY`. Não inventar preços
definitivos.

Subscription: organization, plan, status, price_snapshot,
credits_snapshot, started_at, current_period_start, current_period_end,
next_billing_at, cancel_at_period_end, canceled_at. Status: PENDING,
ACTIVE, PAST_DUE, SUSPENDED, CANCELED.

BILLING-002 reportou `activate(...)`, `renew_current_cycle(...)`,
snapshots, atomicidade, idempotência, cálculo mensal e integração
CreditService. Audite antes de alterar. Implementar
cancel/suspend/reactivate apenas quando a TASK estrutural exigir. Ciclo
mensal deve tratar 28/29/30/31 dias corretamente.

## 11. Créditos

CreditWallet separa `plan_balance`, `purchased_balance`,
`plan_reserved_balance`, `purchased_reserved_balance`; `balance` e
`reserved_balance` são compatibilidade.

Créditos do plano expiram no fim do ciclo e não acumulam. Créditos
avulsos acumulam e não expiram na renovação. Ordem de consumo: plano
primeiro, avulsos depois.

CreditService é autoridade. Preservar reserve, consume,
refund_reservation, renew_plan_credits, add_purchased_credits e futuros
ajustes. Usar `transaction.atomic`, `select_for_update`, idempotência e
impedir saldo negativo.

Renovação: saldo restante do plano expira, nova franquia entra,
purchased_balance permanece.

Ajuste administrativo: somente SuperAdmin, exigindo organização,
quantidade e motivo, com actor, antes/depois, timestamp e reason. Sempre
via CreditService.

## 12. AI Foundation

Fluxos já validados: STILL e BODY_DETAIL. Preservar Generation,
GenerationRule, SceneTemplate, GeneratedImage, PromptEngine,
OpenAIImageProvider e ModelReference.

AI-001 reportou ModelReference com model, admin, serializer, endpoint
autenticado, listagem ativa, seed, migrations e testes. Campos
reportados: id, code, name, slug, description, prompt_instruction,
preview_image, skin_tone, hair_color, age_range, is_active, sort_order,
created_at, updated_at. Conceito atual: biblioteca global da plataforma.
Não recriar nem tornar tenant-owned sem decisão explícita.

OpenAIImageProvider encapsula SDK/API. PromptEngine centraliza prompts.
GenerationService coordena geração. Não espalhar chamadas OpenAI.

Fidelidade da joia: preservar formato, pedras, quantidade, estrutura,
cor, material, proporção e escala. Não inventar elementos nem definir
sozinho conteúdo criativo final.

Generation deve preservar `create_request()` e `process()`:
`CREATED → CREDIT_RESERVED → PROCESSING → COMPLETED`; falha libera
reserva e termina FAILED. Falha técnica não consome crédito
definitivamente. Preservar idempotency_key.

## 13. Produtos e frontend

Product/ProductAsset preservam histórico. Exclusão comum é
`ACTIVE → ARCHIVED`, nunca remoção física silenciosa.

Frontend estrutural: Dashboard, Perfil, Minhas Peças, Minhas Criações,
Criar, AppShell, navegação desktop/mobile, ProfileProvider e
CreditWalletProvider.

Não deixar botão sem ação, rota inexistente, erro silencioso ou dado
fictício.

Mobile: Início, Criações, Criar, Peças, Perfil.

Dashboard conta apenas Generation COMPLETED e Product ACTIVE. Filtros e
últimas criações devem permanecer coerentes.

Perfil preserva name, email, role, role_label, organization e
is_superuser. PATCH comum nunca promove is_superuser.

## 14. Segurança e migrations

Requests mutáveis: `credentials: include`, `X-CSRFToken`, cookie
csrftoken. Nunca usar csrf_exempt como atalho.

Segredos fora do Git e dos logs.

Nunca apagar migrations, zerar banco ou editar histórico aplicado
arbitrariamente. Usar migrations/data migrations preservando dados.

Pendência histórica de accounts/manager deve ser auditada e, se ainda
existir, tratada como Foundation própria.

## 15. Testes

Por TASK, execute testes proporcionais ao risco.

Backend:

``` bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Frontend:

``` bash
npm run lint
npm run build
```

Billing deve cobrir plano inativo, ciclo inválido, ativação, snapshots,
datas, fim de mês, idempotência, renovação, purchased preservado,
rollback e assinatura incompatível.

AI deve cobrir ModelReference, seed/listagem, migrations e contratos sem
chamar OpenAI real na suíte comum.

SuperAdmin deve cobrir autorização global, 403 de usuário comum,
isolamento, ajustes e auditoria.

Não avance com regressão criada pela TASK.

## 16. Pagamentos

Não integrar pagamento real antes de validar Plan, Subscription,
SubscriptionService, ciclo de créditos, SuperAdmin mínimo e escolha de
plano.

Gateway exige decisão humana. Sucesso do frontend nunca comprova
pagamento; confirmação deve ser server-side confiável.

## 17. Fases macro

Seguir PLAN.md como roteiro detalhado.

A. Consolidar branches/tasks existentes\
B. Finalizar Foundation\
C. Finalizar Billing\
D. Validar ciclo completo de créditos\
E. Evoluir AI Foundation estrutural\
F. Construir SuperAdmin Foundation\
G. Estrutura comercial do cliente\
H. Minhas Criações estrutural\
I. Preparar camada de pagamentos sem escolher gateway\
J. Hardening estrutural\
K. Auditoria final para STRUCTURAL_READY

Checkpoint de toda TASK:

`IMPLEMENTAÇÃO → TESTES → AUDITORIA → DOCUMENTAÇÃO → GIT DIFF → COMMIT → WORKING TREE CLEAN → PRÓXIMA TASK`

## 18. Definição de STRUCTURAL_READY

O modo autônomo termina quando existir infraestrutura estável e testada
para:

1.  identidade/perfil;
2.  organizações;
3.  SuperAdmin;
4.  Plan;
5.  Subscription;
6.  ciclo de assinatura;
7.  CreditWallet;
8.  créditos do plano;
9.  créditos avulsos;
10. ajustes administrativos;
11. Product;
12. Generation;
13. GenerationRule;
14. SceneTemplate;
15. ModelReference;
16. PromptEngine;
17. OpenAIImageProvider;
18. modos de geração configuráveis;
19. APIs estruturais necessárias;
20. frontend capaz de consumir essas estruturas;
21. testes estruturais;
22. documentação sincronizada.

Não é necessário para STRUCTURAL_READY: pagamentos reais, prompts
finais, estilos finais, preços comerciais definitivos ou deploy de
produção.

Antes de declarar o marco, faça auditoria integral de Git, documentação,
models, migrations, services, APIs, permissions, multi-tenancy, Billing,
Credits, AI, SuperAdmin, frontend e testes.

## 19. Parada antes dos prompts e estilos

Ao atingir `STRUCTURAL_READY`, **PARE**.

Não escreva automaticamente os prompts finais. Não invente estilos.

Os modos visuais finais, incluindo Still, Detalhe no Corpo,
Instagramável, Na Modelo e futuros estilos, serão definidos/validados
pelo responsável pelo produto.

A infraestrutura deve ficar pronta para recebê-los.

## 20. Relatório final obrigatório

Entregue:

``` text
# MARIED STUDIO — STRUCTURAL_READY

## Estado Git
## Arquitetura final
## Foundation
## Billing
## Credits
## SuperAdmin
## AI Foundation
## Models
## Services
## APIs
## Frontend
## Migrations
## Testes
## Documentação atualizada
## Commits realizados
## Dívidas técnicas
## Riscos
## Decisões aguardando produto
## Prompts pendentes
## Estilos pendentes
## Arquivos que receberão prompts
## Próximo marco recomendado
```

Depois aguarde o responsável pelo produto.

## 21. Regra final

Quando velocidade e integridade entrarem em conflito, preserve
integridade.

Autonomia técnica não significa autonomia de produto.
