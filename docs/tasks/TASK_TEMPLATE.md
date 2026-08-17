# TASK_TEMPLATE.md - MARIED STUDIO

## ID
`<ID>`

## Título
`<título curto>`

## Status
`BLOCKED | READY | IN_PROGRESS | REVIEW | VALIDATED`

## Owner / Workstream
`FOUNDATION | BILLING | BODY_DETAIL | INSTAGRAMABLE | ON_MODEL | FRONTEND_INTEGRATION | SUPERADMIN | TESTS_QA`

## Objetivo
Uma única entrega verificável.

## Contexto obrigatório
Ler:
- `AGENTS.md`
- `PRD.md`
- `SPEC.md`
- `ADR.md`
- `PLAN.md`
- `PROJECT_STATE.md`
- arquivos reais relacionados à tarefa

## DEPENDS_ON
- `<task id ou NONE>`

## BLOCKS
- `<task id ou NONE>`

## Arquivos permitidos
- `<path>`

## Arquivos proibidos
- `<path/domínio>`

## Shared files / lock required
`LOCK_REQUIRED: true | false`

Shared files:
- `<path>`

## Implementação esperada
- item 1
- item 2
- item 3

## Não fazer
- não ampliar escopo;
- não alterar arquitetura sem decisão;
- não tocar prompts validados sem autorização;
- adicionar restrições específicas da tarefa.

## Critérios de aceite
- [ ] critério 1
- [ ] critério 2
- [ ] critério 3

## Testes obrigatórios
```bash
<comandos>
```

## Validação manual
Descrever quando aplicável.

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
