# PLAN.md - MARIED STUDIO

Plano sequencial de implementação para os quatro modos oficiais de geração.

## Fase 0 - Auditoria inicial

Status: obrigatória antes de implementar.

Tarefas:

- localizar `apps/ai/services/prompt_engine.py`;
- confirmar os modos existentes `STILL`, `BODY_DETAIL`, `INSTAGRAM` e `MODEL`;
- localizar `SceneTemplate`, `GenerationRule`, serviços de geração, endpoints e frontend;
- identificar onde hoje aparecem as opções `Elegante`, `Luxuoso`, `Editorial` e `Natural`;
- confirmar fluxo atual de crédito;
- registrar riscos antes de alterar código.

Critério de aceite:

- estado real do código documentado antes da primeira alteração.

## Fase 1 - Proteção dos prompts validados

Status: prioridade alta.

Tarefas:

- marcar em documentação e, se fizer sentido no código, com comentário objetivo, que `STILL` é validado;
- marcar que `("EARRING", "BODY_DETAIL")` é validado;
- garantir que alterações futuras não reescrevam esses blocos;
- criar teste de regressão textual ou comportamental quando viável.

Critério de aceite:

- Still continua igual;
- Earring + Body Detail preserva fidelidade, anatomia, escala e composição.

## Fase 2 - Criar ModelReference

Status: planejada.

Tarefas:

- criar entidade `ModelReference`;
- criar migration;
- registrar no Admin ou SuperAdmin;
- criar serializer/API quando necessário;
- criar seed inicial com quatro modelos;
- expor listagem apenas de modelos ativos;
- ordenar por `sort_order`.

Modelos iniciais:

- pele clara, cabelo loiro, 25 a 28 anos;
- pele clara, cabelo preto, 25 a 28 anos;
- pele clara, cabelo ruivo, 25 a 28 anos;
- pele negra, cabelo escuro, 25 a 28 anos.

Critério de aceite:

- frontend e backend conseguem listar modelos ativos;
- `ModelReference` não depende de `SceneTemplate`.

## Fase 3 - BODY_DETAIL para todas as categorias

Status: parcialmente implementada.

Tarefas:

- remover direções visuais como escolha do usuário para `BODY_DETAIL` no contrato backend;
- exigir `model_reference_id`;
- mapear área corporal automaticamente por categoria;
- preservar regra validada de `EARRING`;
- criar regras especializadas para `NECKLACE + BODY_DETAIL`, `RING + BODY_DETAIL`, `BRACELET + BODY_DETAIL` e `ANKLET + BODY_DETAIL`;
- garantir que a peça continue protagonista.

Mapeamento oficial:

| Categoria | Área |
| --- | --- |
| `EARRING` | orelha/lateral do rosto |
| `NECKLACE` | pescoço/colo |
| `RING` | mão/dedos |
| `BRACELET` | pulso/braço |
| `ANKLET` | tornozelo/pé/perna |

Critério de aceite:

- usuário escolhe modelo;
- sistema escolhe área corporal;
- cada categoria possui regra especializada;
- geração consome 1 crédito.

Implementado em `AI-002`:

- `BODY_DETAIL` exige `model_reference_id` e rejeita `scene_template_id`.
- `Generation` preserva vínculo com `ModelReference`.
- `PromptEngine` recebe instrução da `ModelReference`.
- Contratos de payload para `STILL`, `INSTAGRAM` e `MODEL` também rejeitam combinações inválidas.

## Fase 4 - Cenários Instagramáveis

Status: parcialmente implementada.

Tarefas:

- confirmar compatibilidade atual de `SceneTemplate`;
- limitar uso oficial de `SceneTemplate` ao modo `INSTAGRAM` na V1;
- criar cadastro SuperAdmin de cenários;
- permitir nome, prompt, imagem de preview, status ativo, ordem e versão;
- criar cenários iniciais se definidos pelo produto;
- listar cenários ativos no frontend.

Critério de aceite:

- Instagramável exige cenário;
- cenário é administrável pelo SuperAdmin;
- geração consome 1 crédito.

Implementado em `AI-003`:

- listagem pública autenticada retorna somente `SceneTemplate` ativo de `INSTAGRAM`;
- `BODY_DETAIL` não lista `SceneTemplate`;
- SuperAdmin lista, cria e edita cenários Instagramáveis;
- SuperAdmin rejeita `SceneTemplate` fora de `INSTAGRAM` na V1;
- `seed_studio` cria apenas `SceneTemplate` de `INSTAGRAM`.

## Fase 5 - MODEL / Na Modelo

Status: parcialmente implementada.

Tarefas:

- exibir `MODEL` como Na Modelo;
- exigir `model_reference_id`;
- reutilizar biblioteca `ModelReference`;
- criar regras de enquadramento por categoria;
- decidir automaticamente entre corpo inteiro e 3/4 conforme legibilidade da peça;
- garantir escala real e aplicação anatômica correta.

Critério de aceite:

- usuário escolhe modelo;
- sistema gera composição de modelo com joia;
- peça continua legível;
- geração consome 1 crédito.

Implementado em `AI-004`:

- `MODEL` é exibido como `Na Modelo`;
- `MODEL` exige `model_reference_id` e rejeita `scene_template_id`;
- `Generation` preserva vínculo com `ModelReference`;
- `PromptEngine` recebe instrução da `ModelReference`;
- `seed_studio` cria `GenerationRule` ativa para `MODEL` em todas as categorias.

Pendências de produto:

- validar enquadramento final corpo inteiro ou 3/4 por categoria;
- aprovar composição, poses e legibilidade visual antes de produção.

## Fase 6 - Frontend

Status: implementada estruturalmente.

Tarefas:

- atualizar labels dos modos;
- remover seleção de direção visual do `BODY_DETAIL`;
- adicionar seleção de modelo para Detalhe no Corpo;
- adicionar seleção de cenário para Instagramável;
- adicionar seleção de modelo para Na Modelo;
- impedir combinações inválidas;
- mostrar previews quando disponíveis;
- manter experiência simples.

Critério de aceite:

- cada modo mostra apenas a escolha adicional correta;
- Still não mostra escolha adicional;
- o usuário não escolhe manualmente área corporal.

Implementado em `FRONT-001`:

- labels oficiais dos quatro modos;
- `STILL` sem seleção adicional;
- `BODY_DETAIL` e `MODEL` com seleção de `ModelReference`;
- `INSTAGRAM` com seleção de `SceneTemplate`;
- payloads enviados sem combinações inválidas.

Pendências:

- validação autenticada com upload/geração real;
- ajuste visual fino com validação humana.

## Fase 7 - API, créditos e validações

Status: planejada.

Tarefas:

- validar payload por modo;
- rejeitar combinações inválidas;
- aplicar `1 geração = 1 crédito`;
- garantir idempotência e refund conforme regra existente;
- atualizar documentação da API se existir.

Critério de aceite:

- todos os modos consomem 1 crédito por geração;
- falhas não causam cobrança duplicada;
- payload inválido retorna erro claro.

## Fase 8 - Testes

Status: implementada estruturalmente.

Tarefas:

- testes de unidade do mapeamento de área corporal;
- testes do PromptEngine por modo;
- testes de validação de payload;
- testes de crédito;
- testes de listagem de `ModelReference`;
- testes de listagem de `SceneTemplate`;
- teste de regressão para `STILL`;
- teste de regressão para `EARRING + BODY_DETAIL`.

Critério de aceite:

- testes críticos passam antes de produção.

Implementado em `QA-001`:

- auditoria final passou com `python manage.py check`;
- sem migrations pendentes;
- suíte Django passou com 40 testes;
- `npm run lint` passou;
- `npm run build` passou.

## Fase 9 - Validação visual antes de produção

Status: planejada.

Tarefas:

- validar Still;
- validar Detalhe no Corpo por categoria;
- validar Instagramável com cenários oficiais;
- validar Na Modelo por categoria;
- aprovar manualmente resultados antes de liberar.

Critério de aceite:

- nenhum modo novo vai para produção sem validação visual humana.

## Fase 10 - Produção

Status: planejada.

Tarefas:

- revisar migrations;
- revisar variáveis de ambiente;
- executar testes finais;
- criar plano de rollback;
- publicar;
- monitorar erros e consumo de créditos.

Critério de aceite:

- produção liberada com rastreabilidade e rollback possível.

## Modelo de execução por workstreams

As fases continuam sendo o roadmap do produto, mas a execução passa a ser dividida em workstreams independentes quando possível.

### Grafo macro de dependências

```text
FOUNDATION
   │
   ├── BILLING
   │      └── SUPERADMIN comercial
   │
   └── AI-001 ModelReference
          ├── BODY_DETAIL
          └── ON_MODEL

INSTAGRAMABLE
   └── pode avançar em paralelo com ModelReference/Billing
       desde que não dispute arquivos compartilhados

BODY_DETAIL + INSTAGRAMABLE + ON_MODEL
   └── FRONTEND_INTEGRATION
          └── TESTS_QA
               └── VALIDAÇÃO VISUAL
                    └── PRODUÇÃO
```

### Estrutura obrigatória de tarefa

Toda tarefa deve possuir:

- `ID`
- `STATUS`
- `OWNER/WORKSTREAM`
- `DEPENDS_ON`
- `BLOCKS`
- `ARQUIVOS PERMITIDOS`
- `ARQUIVOS PROIBIDOS`
- `SHARED FILES`
- `LOCK_REQUIRED`
- `CRITÉRIOS DE ACEITE`
- `TESTES`

Status oficiais:
- `BLOCKED`
- `READY`
- `IN_PROGRESS`
- `REVIEW`
- `VALIDATED`

## Workstream FOUNDATION

### FOUNDATION-001 - Fechar ProfileProvider

Status: `AUTO_VALIDATED`.

Escopo:
- RootLayout;
- AppShell;
- DashboardHome;
- sincronização do perfil após edição;
- remoção de dados hardcoded.

Não alterar Billing ou PromptEngine.

## Workstream BILLING

### BILLING-001 - Finalizar Plan e Subscription
Status: `AUTO_VALIDATED`.

### BILLING-002 - SubscriptionService
Status: `AUTO_VALIDATED`.

`DEPENDS_ON: BILLING-001`

### BILLING-003 - Testes de ciclo
`DEPENDS_ON: BILLING-002`

### BILLING-004 - APIs comerciais
`DEPENDS_ON: BILLING-002, BILLING-003`

Billing pode avançar em paralelo com workstreams de IA quando não houver conflito de shared files.

## Workstream AI / ModelReference

### AI-001 - Criar ModelReference

Status: `AUTO_VALIDATED`.

Responsabilidades:
- entidade;
- migration;
- admin/API;
- seed dos quatro modelos;
- listagem ativa;
- testes.

`BLOCKS: AI-002, AI-004`

## Workstream BODY_DETAIL

### AI-002 - Detalhe no Corpo

Status: `AUTO_VALIDATED`.

`DEPENDS_ON: AI-001`

Escopo:
- substituir direção visual por ModelReference;
- preservar `EARRING + BODY_DETAIL`;
- preparar contrato para regras por categoria;
- área corporal automática;
- testes.

Pendências de produto:
- aprovar regras visuais finais para colar, anel, pulseira e tornozeleira;
- validar visualmente as saídas antes de produção.

## Workstream INSTAGRAMABLE

### AI-003 - Instagramável

Status: `AUTO_VALIDATED`.

Pode avançar em paralelo com `AI-001` e `BILLING-*` se não disputar shared files.

Escopo:
- SceneTemplate como cenário;
- cadastro/admin;
- API/listagem;
- cenários ativos;
- validações;
- testes.

Pendências de produto:
- definir biblioteca inicial de cenários oficiais;
- aprovar prompts e previews;
- validar visualmente antes de produção.

## Workstream ON_MODEL

### AI-004 - Na Modelo

Status: `AUTO_VALIDATED`.

`DEPENDS_ON: AI-001`

Escopo:
- usar ModelReference;
- regras por categoria;
- corpo inteiro ou 3/4;
- escala/anatomia;
- testes.

Pendências de produto:
- validação visual por categoria;
- prompts finais específicos, se necessários.

## Workstream FRONTEND_INTEGRATION

### FRONT-001 - Fluxos dos quatro modos

Status: `AUTO_VALIDATED`.

`DEPENDS_ON`: contratos backend estabilizados dos modos expostos.

Observação:
Fluxo estrutural implementado. Validação autenticada com upload, geração real e aprovação visual humana continuam necessárias antes de produção.

Escopo:
- Still sem escolha adicional;
- BODY_DETAIL com modelo;
- Instagramável com cenário;
- Na Modelo com modelo;
- bloquear combinações inválidas;
- previews.

## Workstream SUPERADMIN

### ADMIN-001 - Administração global base

Status: `AUTO_VALIDATED`.

Depende de contratos SuperAdmin/Billing estabilizados.

Escopo implementado:
- organizações;
- contas;
- planos;
- assinaturas;
- créditos;
- gerações;
- falhas;
- ajuste administrativo de crédito;
- auditoria.

Pendências futuras:
- frontend dedicado do SuperAdmin;
- administração completa de cenários e `ModelReference`;
- validação de experiência com responsável do produto.

## Workstream TESTS_QA

### QA-001 - Regressão e integração

Status: `AUTO_VALIDATED`.

Depende das features-alvo em `REVIEW`.

Escopo:
- regressão Still;
- regressão EARRING+BODY_DETAIL;
- créditos;
- payloads;
- isolamento;
- integração frontend/backend.

## Execução paralela permitida

Exemplo seguro:

```text
Agente A -> BILLING-001
Agente B -> AI-001
Agente C -> AI-003
```

desde que não disputem shared files.

Exemplo proibido:

```text
Agente A -> AI-002 alterando prompt_engine.py
Agente B -> AI-004 alterando prompt_engine.py
```

ao mesmo tempo, sem coordenação.

## Estrutura de task files

Diretório:

```text
docs/tasks/
```

Arquivos iniciais:

```text
BILLING-001.md
BILLING-002.md
AI-001-model-reference.md
AI-002-body-detail.md
AI-003-instagram.md
AI-004-on-model.md
FRONT-001.md
ADMIN-001.md
QA-001.md
```

Usar `docs/tasks/TASK_TEMPLATE.md` como base.
