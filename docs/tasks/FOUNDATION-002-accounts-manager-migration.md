# FOUNDATION-002 - Registrar migration do UserManager

## ID
`FOUNDATION-002`

## Título
`Registrar migration pendente de accounts`

## Status
`REVIEW`

## Owner / Workstream
`FOUNDATION`

## Objetivo
Resolver a pendência detectada por `makemigrations --check` em `accounts`, registrando a alteração de manager do `User` em uma migration própria, sem alterar lógica de autenticação, perfil, organização ou permissões.

## Contexto obrigatório
Ler:
- `AGENTS.md`
- `PRD.md`
- `SPEC.md`
- `ADR.md`
- `PLAN.md`
- `PROJECT_STATE.md`
- `apps/accounts/models.py`
- migrations existentes de `apps/accounts`

## DEPENDS_ON
- `FOUNDATION-001`

## BLOCKS
- Consolidação limpa de checks globais

## Arquivos permitidos
- `docs/tasks/FOUNDATION-002-accounts-manager-migration.md`
- `apps/accounts/migrations/0002_alter_user_managers.py`

## Arquivos proibidos
- `apps/accounts/models.py`
- `apps/accounts/serializers.py`
- `apps/accounts/views.py`
- `apps/credits/**`
- `apps/billing/**`
- `apps/ai/**`
- `frontend/**`

## Shared files / lock required
`LOCK_REQUIRED: false`

Shared files:
- Nenhum

## Implementação esperada
- Gerar a migration pendente indicada pelo Django.
- Não alterar código de runtime.
- Confirmar que `makemigrations --check --dry-run` passa após a migration.

## Não fazer
- Não alterar `UserManager`.
- Não mudar autenticação.
- Não mudar regras de `is_superuser`.
- Não alterar isolamento por organização.
- Não refatorar perfil ou serializers.

## Critérios de aceite
- [ ] Migration criada em `apps/accounts/migrations/`.
- [ ] `python manage.py makemigrations --check --dry-run` passa.
- [ ] `python manage.py check` passa.
- [ ] `python manage.py test --keepdb` passa.
- [ ] Working tree final limpo após commit.

## Testes obrigatórios
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --keepdb
```

## Validação manual
Não aplicável. A task apenas registra migration de estado do modelo Django.

## Relatório final obrigatório

### Implementado
Resumo.

### Arquivos alterados
Lista.

### Banco
Migrations e impacto.

### Validações executadas
Comandos e resultados.

### Shared files / locks
Informar uso/liberação.

### Riscos ou pendências
Somente riscos reais.

### Próximo passo
Uma única continuação lógica.
