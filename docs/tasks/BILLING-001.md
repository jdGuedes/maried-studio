# BILLING-001 - Finalizar Plan e Subscription

## Status
`AUTO_VALIDATED`

## Owner / Workstream
`BILLING`

## Objetivo
Executar somente esta entrega, respeitando `AGENTS.md` e `PLAN.md`.

## DEPENDS_ON
`NONE`

## BLOCKS
Consultar `PLAN.md`.

## Arquivos permitidos
- `apps/billing/models.py`
- `apps/billing/admin.py`
- `apps/billing/migrations/**`
- `apps/billing/tests.py`
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
- `Plan` implementado.
- `Subscription` implementada.
- Snapshots comerciais preservados.
- Relação organização/assinatura protegida.
- Admin Django registrado.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.billing --keepdb
python manage.py test --keepdb
```

## Relatório final
Implementado e consolidado na branch `agent/STRUCTURAL-READY`.

Resultado:

- `Plan`, `Subscription`, ciclo mensal, status e snapshots estruturais implementados.
- Pagamento real e preços finais permanecem fora de `STRUCTURAL_READY`.
