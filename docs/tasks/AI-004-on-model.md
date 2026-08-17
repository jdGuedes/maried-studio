# AI-004 - Implementar Na Modelo com ModelReference

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`ON_MODEL`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`AI-001`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/studio/tests.py`
- `docs/tasks/AI-004-on-model.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- prompts finais do modo `MODEL / Na Modelo`.
- biblioteca visual final de poses, roupas, fundos ou estilos.
- regras de crédito, billing ou gateway.
- `SceneTemplate` como recurso principal do modo `MODEL`.
- UI final do frontend.

## Shared files / lock required
`LOCK_REQUIRED: false`

## Critérios de aceite
- `MODEL` é exibido como `Na Modelo`.
- `MODEL` exige `model_reference_id`.
- `MODEL` rejeita `scene_template_id`.
- `MODEL` reutiliza `ModelReference`.
- `Generation` preserva vínculo com `ModelReference`.
- `PromptEngine` recebe instrução da `ModelReference`.
- Seed estrutural possui `GenerationRule` ativa para `MODEL` em todas as categorias.

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

- `apps/studio/tests.py`
- `docs/tasks/AI-004-on-model.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

### Validações executadas

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `python manage.py test apps.studio --keepdb`: passou, 15 testes.
- `python manage.py test --keepdb`: passou, 40 testes.
- `npm run lint`: passou.
- `npm run build`: passou.

### Resultado

- Contrato estrutural do modo `MODEL / Na Modelo` validado.
- `MODEL` usa `ModelReference`, rejeita `SceneTemplate` e reserva 1 crédito por geração.
- `PromptEngine` recebe a instrução da `ModelReference`.
- `seed_studio` garante `GenerationRule` ativa para `MODEL` em todas as categorias.

### Riscos ou pendências

- Enquadramento visual final corpo inteiro ou 3/4 ainda precisa de validação humana por categoria.
- Prompts finais específicos do modo `MODEL` não foram inventados nem alterados.
- Frontend final de seleção de modelo permanece em `FRONT-001`.

### Decisões que exigem validação humana

- Aprovação visual do modo `MODEL / Na Modelo` por categoria.
- Definição final de poses, composição e critérios de legibilidade visual.
