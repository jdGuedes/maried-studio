# AI-002 - Integrar ModelReference ao BODY_DETAIL

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`BODY_DETAIL`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`AI-001`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/studio/models.py`
- `apps/studio/serializers.py`
- `apps/studio/views.py`
- `apps/studio/services/generation_service.py`
- `apps/studio/tests.py`
- `apps/studio/migrations/**`
- `apps/ai/services/prompt_engine.py`
- `frontend/src/types/api.ts`
- `frontend/src/lib/api.ts`
- `docs/tasks/AI-002-body-detail.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- prompt `STILL`
- reescrita da regra especializada `("EARRING", "BODY_DETAIL")`
- preços, planos, gateway ou regras comerciais
- UI final de escolha visual

## Shared files / lock required
`LOCK_REQUIRED: true`

Shared files:
- `apps/ai/services/prompt_engine.py`
- `apps/studio/models.py`

## Critérios de aceite
- `BODY_DETAIL` exige `model_reference_id`.
- `BODY_DETAIL` rejeita `scene_template_id`.
- `STILL` rejeita `model_reference_id` e `scene_template_id`.
- `INSTAGRAM` exige `scene_template_id` e rejeita `model_reference_id`.
- `MODEL` exige `model_reference_id` e rejeita `scene_template_id`.
- `Generation` preserva vínculo com `ModelReference`.
- PromptEngine recebe instrução da `ModelReference` sem reescrever prompt Still.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.studio --keepdb
python manage.py test --keepdb
npm run lint
npm run build
```

## Relatório final
### Arquivos alterados

- `apps/studio/models.py`
- `apps/studio/serializers.py`
- `apps/studio/views.py`
- `apps/studio/services/generation_service.py`
- `apps/studio/tests.py`
- `apps/studio/migrations/0002_generation_model_reference_alter_generation_mode_and_more.py`
- `apps/ai/services/prompt_engine.py`
- `frontend/src/types/api.ts`
- `frontend/src/lib/api.ts`
- `docs/tasks/AI-002-body-detail.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

### Validações executadas

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `python manage.py test apps.studio --keepdb`: passou, 9 testes.
- `python manage.py test --keepdb`: passou, 31 testes.
- `npm run lint`: passou.
- `npm run build`: passou.

### Resultado

- `BODY_DETAIL` agora exige `model_reference_id`.
- `BODY_DETAIL` rejeita `scene_template_id`.
- `STILL` rejeita `model_reference_id` e `scene_template_id`.
- `INSTAGRAM` exige `scene_template_id` e rejeita `model_reference_id`.
- `MODEL` exige `model_reference_id` e rejeita `scene_template_id`.
- `Generation` preserva vínculo com `ModelReference`.
- `PromptEngine` inclui instrução da `ModelReference`.

### Riscos ou pendências

- Regras visuais finais de `NECKLACE`, `RING`, `BRACELET` e `ANKLET` para `BODY_DETAIL` ainda exigem validação humana de produto.
- Frontend final de escolha de modelo/cenário permanece em `FRONT-001`.

### Decisões que exigem validação humana

- Aprovação visual das novas categorias em `BODY_DETAIL`.
- Aprovação visual do modo `MODEL / Na Modelo`.
