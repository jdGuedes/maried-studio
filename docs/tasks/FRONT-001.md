# FRONT-001 - Integrar quatro modos no frontend

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`FRONTEND_INTEGRATION`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`Contratos backend dos modos`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `frontend/src/types/api.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/create/result-mode-step.tsx`
- `frontend/src/components/create/style-step.tsx`
- `frontend/src/components/create/confirmation-step.tsx`
- `frontend/src/components/create/creation-wizard.tsx`
- `docs/tasks/FRONT-001.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- backend, migrations e prompts.
- regras de crédito, billing ou gateway.
- biblioteca final de cenários/modelos.
- upload/geração real sem sessão autenticada.

## Shared files / lock required
`LOCK_REQUIRED: true`

Shared files:
- `frontend/src/components/create/creation-wizard.tsx`

## Critérios de aceite
- Labels oficiais: Still, Detalhe no Corpo, Instagramável e Na Modelo.
- Still não mostra escolha adicional.
- Detalhe no Corpo lista `ModelReference` ativo e envia `model_reference_id`.
- Na Modelo lista `ModelReference` ativo e envia `model_reference_id`.
- Instagramável lista `SceneTemplate` ativo e envia `scene_template_id`.
- Combinações inválidas não são montadas pelo frontend.
- Confirmação exibe Modelo ou Cenário conforme o modo.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
npm run lint
npm run build
```

## Relatório final
### Arquivos alterados

- `frontend/src/types/api.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/create/result-mode-step.tsx`
- `frontend/src/components/create/style-step.tsx`
- `frontend/src/components/create/confirmation-step.tsx`
- `frontend/src/components/create/creation-wizard.tsx`
- `docs/tasks/FRONT-001.md`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

### Validações executadas

- `python manage.py check`: passou.
- `python manage.py makemigrations --check --dry-run`: passou.
- `npm run lint`: passou.
- `npm run build`: passou.
- Browser em `http://localhost:3000/criar`: página renderizou sem overlay; interação de categoria funcionou.

### Resultado

- Wizard usa labels oficiais dos quatro modos.
- `STILL` segue direto para confirmação sem seleção adicional.
- `BODY_DETAIL` e `MODEL` carregam `ModelReference` e enviam `model_reference_id`.
- `INSTAGRAM` carrega `SceneTemplate` e envia `scene_template_id`.
- Etapa visual foi generalizada para Modelo ou Cenário.
- Confirmação e tela final exibem rótulos amigáveis, não valores internos.

### Riscos ou pendências

- Validação no navegador não executou upload/geração real porque o browser não estava autenticado e upload de arquivo exige confirmação específica.
- Biblioteca final de cenários/modelos e validação visual de produção seguem pendentes de produto.

### Decisões que exigem validação humana

- Aprovar experiência visual final dos cards de Modelo e Cenário.
- Validar fluxo completo autenticado com uma peça real de teste.
