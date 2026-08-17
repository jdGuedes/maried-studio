# BILLING-002 - Criar SubscriptionService

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`BILLING`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`BILLING-001`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/billing/services.py`
- `apps/billing/tests.py`
- `apps/credits/services.py`
- `PROJECT_STATE.md`
- `PLAN.md`
- `SPEC.md`

## Arquivos proibidos
- gateway de pagamento real.
- preços comerciais finais sem aprovação.
- prompts ou IA.

## Shared files / lock required
`LOCK_REQUIRED: false`

## Critérios de aceite
- `SubscriptionService.activate(...)` cria/reativa assinatura com snapshots.
- Plano inativo é rejeitado.
- Renovação mensal recalcula ciclo.
- Créditos do plano são aplicados via `CreditService`.
- Créditos comprados são preservados na renovação.
- Operações críticas são atômicas.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.billing --keepdb
python manage.py test --keepdb
```

## Relatório final
Implementado e consolidado na branch `agent/STRUCTURAL-READY`.

Commit de origem:

- `f339059 feat: implement BILLING-002 subscription service`

Resultado:

- `SubscriptionService.activate(...)` e `renew_current_cycle(...)` implementados com integração a créditos.
- Gateway real permanece fora de `STRUCTURAL_READY`.
