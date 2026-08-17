# AI-003 - Implementar Instagramável com SceneTemplate

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`INSTAGRAMABLE`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`Auditoria de SceneTemplate`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/studio/views.py`
- `apps/studio/tests.py`
- `apps/studio/management/commands/seed_studio.py`
- `apps/superadmin/serializers.py`
- `apps/superadmin/views.py`
- `apps/superadmin/urls.py`
- `apps/superadmin/tests.py`
- `docs/tasks/AI-003-instagram.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- prompts finais de cenários comerciais.
- seed de cenários oficiais sem aprovação de produto.
- regras de crédito, billing ou gateway.
- `ModelReference`.
- UI final do frontend.

## Shared files / lock required
`LOCK_REQUIRED: true`

Shared files:
- `apps/studio/views.py`
- `apps/superadmin/urls.py`

## Critérios de aceite
- `SceneTemplate` é usado oficialmente como cenário do modo `INSTAGRAM`.
- Listagem pública autenticada retorna somente cenários ativos de `INSTAGRAM`.
- `BODY_DETAIL` não lista `SceneTemplate`.
- SuperAdmin consegue listar, criar e editar cenários Instagramáveis.
- SuperAdmin consegue ativar, desativar e ordenar cenários.
- SuperAdmin não consegue criar `SceneTemplate` fora de `INSTAGRAM` na V1.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.studio apps.superadmin --keepdb
python manage.py test --keepdb
npm run lint
npm run build
```

## Relatório final
### Arquivos alterados

- `apps/studio/views.py`
- `apps/studio/tests.py`
- `apps/studio/management/commands/seed_studio.py`
- `apps/superadmin/serializers.py`
- `apps/superadmin/views.py`
- `apps/superadmin/urls.py`
- `apps/superadmin/tests.py`
- `docs/tasks/AI-003-instagram.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

### Validações executadas

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `python manage.py test apps.studio apps.superadmin --keepdb`: passou, 19 testes.
- `python manage.py test --keepdb`: passou, 36 testes.
- `npm run lint`: passou.
- `npm run build`: passou.

### Resultado

- `SceneTemplate` ficou limitado como cenário público de `INSTAGRAM`.
- `BODY_DETAIL` não recebe mais templates pela listagem pública.
- SuperAdmin ganhou endpoints estruturais para listar, criar e editar cenários Instagramáveis.
- Criação de `SceneTemplate` para modos diferentes de `INSTAGRAM` é rejeitada na V1.
- `seed_studio` deixa de criar `SceneTemplate` para `MODEL`, `BODY_DETAIL` ou `STILL`.

### Riscos ou pendências

- Cenários comerciais oficiais não foram criados porque dependem de aprovação de produto.
- UI final de seleção de cenário permanece em `FRONT-001`.

### Decisões que exigem validação humana

- Definir biblioteca inicial de cenários Instagramáveis.
- Validar visualmente os prompts e previews oficiais antes de produção.
