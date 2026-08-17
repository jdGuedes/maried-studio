# ADMIN-001 - Criar base do painel SuperAdmin

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`SUPERADMIN`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`FOUNDATION-001, BILLING-001, BILLING-002`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/superadmin/**`
- `apps/credits/services.py`
- `config/settings.py`
- `config/urls.py`
- `docs/tasks/ADMIN-001.md`
- `PROJECT_STATE.md`
- `PLAN.md`

## Arquivos proibidos
- `apps/ai/services/prompt_engine.py`
- prompts validados
- regras comerciais de preço/plano
- gateway de pagamento
- frontend fora de documentação de pendências

## Shared files / lock required
`LOCK_REQUIRED: true`

Shared files:
- `config/settings.py`
- `config/urls.py`

## Critérios de aceite
- SuperAdmin autenticado consegue consultar dashboard estrutural.
- SuperAdmin consegue listar organizações, contas, planos, assinaturas, carteiras e gerações.
- Usuário comum recebe 403 nos endpoints globais.
- Ajuste administrativo de crédito passa por `CreditService`.
- Ajuste registra `actor`, motivo, snapshots antes/depois e `AuditLog`.
- Ajuste não permite saldo negativo.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.superadmin --keepdb
python manage.py test --keepdb
npm run lint
npm run build
```

## Relatório final
### Implementado
- App `apps.superadmin`.
- Endpoints globais protegidos por `is_superuser`.
- Listagens estruturais de organizações, contas, planos, assinaturas, carteiras e gerações.
- Dashboard estrutural com contagens globais.
- Ajuste administrativo de crédito via `CreditService.adjust_credits`.
- Registro de `CreditTransaction` com actor, motivo e snapshots.
- Registro complementar em `AuditLog`.

### Arquivos alterados
- `apps/superadmin/**`
- `apps/credits/services.py`
- `config/settings.py`
- `config/urls.py`
- `docs/tasks/ADMIN-001.md`

### Banco
Sem nova migration.

### Validações executadas
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test apps.superadmin --keepdb`
- `python manage.py test --keepdb`
- `npm run lint`
- `npm run build`

### Shared files / locks
`config/settings.py` e `config/urls.py` alterados nesta task. Lock lógico liberado ao fim da implementação.

### Riscos ou pendências
- Ainda falta frontend SuperAdmin dedicado.
- Ainda falta validar experiência administrativa com responsável do produto.

### Próximo passo
Auditar contratos de modos de geração para identificar a próxima lacuna estrutural rumo a `STRUCTURAL_READY`.
