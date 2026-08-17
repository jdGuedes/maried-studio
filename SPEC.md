# SPEC.md - MARIED STUDIO

## Escopo técnico

Este documento define o contrato técnico para implementação dos modos de geração do MARIED STUDIO.

O código real deve ser inspecionado antes de qualquer alteração. A documentação registra a direção oficial, mas não substitui a leitura da implementação existente.

## Arquitetura de geração

O `PromptEngine` atual já contém os modos:

- `STILL`
- `BODY_DETAIL`
- `INSTAGRAM`
- `MODEL`

Esses valores internos devem ser preservados.

Mapeamento de exibição:

| Valor interno | Label |
| --- | --- |
| `STILL` | Still |
| `BODY_DETAIL` | Detalhe no Corpo |
| `INSTAGRAM` | Instagramável |
| `MODEL` | Na Modelo |

## Contrato por modo

### STILL

Entrada adicional: nenhuma.

Saída esperada:

- produto isolado;
- fundo branco;
- alta fidelidade;
- sem corpo;
- sem modelo;
- sem cenário.

Prompt validado: preservar sem reescrita.

### BODY_DETAIL

Entrada adicional:

- `model_reference_id`

Entrada derivada:

- `body_area`, calculada pela categoria.

Não usar `SceneTemplate` para `BODY_DETAIL`.

Mapeamento:

| Categoria | `body_area` |
| --- | --- |
| `EARRING` | `EAR_SIDE_FACE` |
| `NECKLACE` | `NECK_CHEST` |
| `RING` | `HAND_FINGERS` |
| `BRACELET` | `WRIST_ARM` |
| `ANKLET` | `ANKLE_FOOT_LEG` |

Regra especializada `("EARRING", "BODY_DETAIL")`: preservar integralmente.

### INSTAGRAM

Entrada adicional:

- `scene_template_id`

Usa:

- `SceneTemplate`

Não usar `ModelReference` para `INSTAGRAM` na V1.

### MODEL

Entrada adicional:

- `model_reference_id`

Enquadramento:

- corpo inteiro ou 3/4;
- escolha automática conforme categoria e legibilidade da peça.

Usa:

- `ModelReference`

Não usar `SceneTemplate` como recurso principal do modo Na Modelo na V1.

Contrato estrutural implementado:

- `MODEL` rejeita `scene_template_id`;
- `MODEL` preserva `model_reference` na geração;
- `PromptEngine` recebe a instrução da `ModelReference`;
- `seed_studio` cria `GenerationRule` ativa para `MODEL` por categoria.

Ainda exige validação humana:

- enquadramento final corpo inteiro ou 3/4 por categoria;
- poses, composição e legibilidade visual da peça.

## Entidades

### SceneTemplate

Entidade existente e estruturada para a arquitetura atual.

Uso oficial:

- cenários do modo Instagramável.

Campos esperados:

- `id`
- `name`
- `slug`
- `prompt_template`
- `preview_image`
- `mode`
- `is_active`
- `sort_order`
- `version`

O SuperAdmin deve conseguir cadastrar, editar, ativar, desativar e ordenar cenários.

Na V1, `SceneTemplate` é aceito apenas para `INSTAGRAM`.

### ModelReference

Entidade implementada.

Uso oficial:

- Detalhe no Corpo;
- Na Modelo.

Campos sugeridos:

- `id`
- `name`
- `slug`
- `description`
- `prompt_instruction`
- `preview_image`
- `skin_tone`
- `hair_color`
- `age_range`
- `is_active`
- `sort_order`
- `created_at`
- `updated_at`

Dados seed iniciais:

| Slug | Descrição |
| --- | --- |
| `light-skin-blonde` | Mulher de 25 a 28 anos, pele clara, cabelo loiro |
| `light-skin-black-hair` | Mulher de 25 a 28 anos, pele clara, cabelo preto |
| `light-skin-red-hair` | Mulher de 25 a 28 anos, pele clara, cabelo ruivo |
| `black-skin-dark-hair` | Mulher de 25 a 28 anos, pele negra, cabelo escuro |

## PromptEngine

Regra de montagem estrutural:

```text
if mode == STILL:
    usar prompt Still validado
    não exigir escolha adicional

if mode == BODY_DETAIL:
    usar prompt Body Detail
    usar regra especializada por categoria
    usar ModelReference
    calcular área corporal automaticamente

if mode == INSTAGRAM:
    usar SceneTemplate

if mode == MODEL:
    usar ModelReference
    aplicar regra de enquadramento por categoria
```

## Proteções obrigatórias

Não reescrever ou otimizar sem autorização:

- prompt `STILL`;
- prompt especializado `("EARRING", "BODY_DETAIL")`.

Ao adaptar `BODY_DETAIL` para `ModelReference`, remover apenas a parte hardcoded de descrição da modelo quando ela existir, preservando regras de anatomia, escala, fidelidade e composição.

## API

O endpoint de criação deve aceitar os campos necessários ao modo escolhido.

Campos conceituais:

- `product_id`
- `category`
- `mode`
- `scene_template_id`
- `model_reference_id`

Validações:

- `STILL`: rejeitar `scene_template_id` e `model_reference_id` se não forem necessários.
- `BODY_DETAIL`: exigir `model_reference_id` e rejeitar `scene_template_id`.
- `INSTAGRAM`: exigir `scene_template_id` e rejeitar `model_reference_id`.
- `MODEL`: exigir `model_reference_id` e rejeitar `scene_template_id`.
- rejeitar combinações inválidas.

Implementado:

- `Generation.model_reference` preserva a referência escolhida.
- `PromptEngine.build(...)` aceita `model_reference`.
- `SceneTemplate` é filtrado para não atender `BODY_DETAIL` quando o modo é informado.

### SuperAdmin

Endpoints estruturais globais:

- `GET /api/superadmin/summary/`
- `GET /api/superadmin/organizations/`
- `GET /api/superadmin/accounts/`
- `GET /api/superadmin/plans/`
- `GET /api/superadmin/subscriptions/`
- `GET /api/superadmin/credit-wallets/`
- `GET /api/superadmin/generations/`
- `GET /api/superadmin/scene-templates/`
- `POST /api/superadmin/scene-templates/`
- `GET /api/superadmin/scene-templates/<id>/`
- `PATCH /api/superadmin/scene-templates/<id>/`
- `PUT /api/superadmin/scene-templates/<id>/`
- `POST /api/superadmin/credit-adjustments/`

Todos exigem usuário autenticado com `is_superuser=true`.
Usuário autenticado comum deve receber 403.

`POST /api/superadmin/credit-adjustments/`:

- `organization_id`
- `amount`
- `balance_type`: `PLAN` ou `PURCHASED`
- `reason`

O ajuste deve passar por `CreditService`, impedir saldo negativo e registrar transação com `actor`, motivo e snapshots antes/depois. Também deve registrar `AuditLog`.

SuperAdmin `SceneTemplate`:

- aceita apenas `generation_mode=INSTAGRAM`;
- permite cadastro, edição, ativação, desativação e ordenação;
- não define biblioteca oficial de cenários sem aprovação de produto.

Seed estrutural:

- `seed_studio` cria regras de geração por modo, mas cria `SceneTemplate` apenas para `INSTAGRAM`.

## Frontend

Labels:

- Still
- Detalhe no Corpo
- Instagramável
- Na Modelo

Fluxo:

- Still: seleção direta.
- Detalhe no Corpo: seleção de modelo.
- Instagramável: seleção de cenário.
- Na Modelo: seleção de modelo.

O frontend não deve expor ao usuário a escolha manual da área corporal em `BODY_DETAIL`; isso é regra do sistema.

Contrato estrutural implementado:

- `STILL` envia `scene_template_id=null` e `model_reference_id=null`;
- `BODY_DETAIL` carrega modelos ativos e envia `model_reference_id`;
- `MODEL` carrega modelos ativos e envia `model_reference_id`;
- `INSTAGRAM` carrega cenários ativos e envia `scene_template_id`;
- confirmação exibe Modelo ou Cenário conforme o modo.

Ainda exige validação humana:

- upload e geração real em sessão autenticada;
- polimento visual final dos cards de Modelo e Cenário.

## Créditos

Regra V1:

```text
1 geração = 1 crédito
```

Aplicar igualmente a todos os modos. Não criar multiplicadores por modo na V1.

## Testes mínimos

- Validação de payload por modo.
- Cálculo de área corporal por categoria no `BODY_DETAIL`.
- Uso de `ModelReference` em `BODY_DETAIL`.
- Uso de `SceneTemplate` em `INSTAGRAM`.
- Uso de `ModelReference` em `MODEL`.
- Still sem escolha adicional.
- Consumo de 1 crédito por geração.
- Proteção contra combinações inválidas.
- Regressão do prompt `EARRING + BODY_DETAIL`.

## Modelo técnico de concorrência entre agentes

O desenvolvimento pode ser executado por múltiplos agentes, mas o repositório deve ser tratado como sistema concorrente com boundaries explícitos.

### Workstreams

```text
FOUNDATION
BILLING
BODY_DETAIL
INSTAGRAMABLE
ON_MODEL
FRONTEND_INTEGRATION
SUPERADMIN
TESTS_QA
```

### Boundaries por domínio

#### BILLING
Responsabilidade principal:
```text
apps/billing/**
apps/credits/** somente quando a tarefa exigir integração de crédito
```
Não alterar IA ou prompts.

#### BODY_DETAIL
Responsabilidade:
- regras de Detalhe no Corpo;
- integração ModelReference;
- mapeamento corporal;
- testes relacionados.

Shared file provável:
`apps/ai/services/prompt_engine.py`

#### INSTAGRAMABLE
Responsabilidade:
- SceneTemplate;
- cenários;
- API/listagem;
- integração de `INSTAGRAM`.

Não alterar ModelReference sem dependência explícita.

#### ON_MODEL
Responsabilidade:
- modo interno `MODEL`;
- ModelReference;
- regras por categoria;
- enquadramento 3/4/corpo inteiro.

Shared file provável:
`apps/ai/services/prompt_engine.py`

#### FRONTEND_INTEGRATION
Responsabilidade:
`frontend/**`

Não inventar payloads ou contratos. Consumir APIs estabilizadas.

### Shared files

Arquivos de integração exigem coordenação:
```text
apps/ai/services/prompt_engine.py
apps/studio/models.py
config/settings.py
config/urls.py
frontend/src/app/layout.tsx
frontend/src/components/layout/app-shell.tsx
```

O caminho real deve ser confirmado no repositório.

### Lock

Tarefa que edita shared file deve declarar:
`LOCK_REQUIRED: true`

Se outro workstream estiver modificando o mesmo arquivo, a tarefa deve aguardar ou virar uma tarefa específica de integração.

### Dependências técnicas

```text
AI-001 ModelReference
    ├── AI-002 BODY_DETAIL
    └── AI-004 ON_MODEL
```

`AI-003 INSTAGRAMABLE` não depende de ModelReference.

`FRONT-001` depende dos contratos backend dos modos que pretende integrar.

### Contratos antes da UI

Antes da integração frontend:
- endpoint conhecido;
- campos conhecidos;
- validações conhecidas;
- resposta conhecida;
- estados de erro conhecidos.

### Integração final

Quando dois workstreams exigirem o mesmo shared file:
1. concluir um;
2. validar;
3. integrar;
4. aplicar o segundo patch;

ou criar tarefa específica de integração.

Evitar merge automático de regras de domínio sensíveis.
