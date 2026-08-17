# AI-001 - Criar ModelReference

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`BODY_DETAIL / ON_MODEL base`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`NONE`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/ai/models.py`
- `apps/ai/admin.py`
- `apps/ai/serializers.py`
- `apps/ai/views.py`
- `apps/ai/urls.py`
- `apps/ai/migrations/**`
- `apps/ai/tests.py`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- prompts finais.
- regras de crédito, billing ou gateway.
- `SceneTemplate` como substituto de `ModelReference`.

## Shared files / lock required
`LOCK_REQUIRED: false`

## Critérios de aceite
- `ModelReference` existe como entidade global.
- Listagem autenticada retorna apenas modelos ativos.
- Seed inicial cria `MODEL_01` a `MODEL_04`.
- Admin Django registra a entidade.
- `ModelReference` não depende de `SceneTemplate`.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.ai --keepdb
python manage.py test --keepdb
```

## Relatório final
Implementado e consolidado na branch `agent/STRUCTURAL-READY`.

Commit de origem:

- `19a2ca8 feat: implement AI-001 model reference`

Resultado:

- `ModelReference` implementado com API autenticada, admin, seed/data migration e testes.
- Usado estruturalmente por `BODY_DETAIL` e `MODEL`.
