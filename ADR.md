# ADR.md - MARIED STUDIO

## ADR-001 - Preservar valores internos dos modos

Status: aprovado.

Decisão:

Manter os valores internos atuais:

- `STILL`
- `BODY_DETAIL`
- `INSTAGRAM`
- `MODEL`

Consequência:

O frontend pode exibir nomes amigáveis sem exigir migration ou renomear dados existentes.

## ADR-002 - Still é prompt validado

Status: aprovado.

Decisão:

O prompt de `STILL` deve ser preservado.

Consequência:

Agentes e desenvolvedores não podem reescrever ou otimizar esse prompt sem autorização explícita.

## ADR-003 - BODY_DETAIL permanece Detalhe no Corpo

Status: aprovado.

Decisão:

`BODY_DETAIL` continua sendo o modo Detalhe no Corpo.

Ele não será renomeado para Close nem transformado em modo genérico de aproximação.

Consequência:

A categoria da peça define automaticamente a área corporal.

## ADR-004 - EARRING + BODY_DETAIL é regra validada

Status: aprovado.

Decisão:

A regra especializada `("EARRING", "BODY_DETAIL")` no `PromptEngine` é validada e deve ser preservada.

Consequência:

A implementação de `ModelReference` pode substituir a descrição hardcoded da modelo, mas não pode remover as regras de fidelidade, escala, anatomia, placement e composição já validadas.

## ADR-005 - Criar ModelReference

Status: aprovado para implementação planejada.

Decisão:

Criar a entidade `ModelReference` para representar modelos reutilizáveis.

Motivo:

Modelo e cenário são conceitos diferentes. `SceneTemplate` não deve ser usado para representar pessoas/modelos.

Usos:

- `BODY_DETAIL`;
- `MODEL`.

## ADR-006 - Biblioteca inicial de quatro modelos

Status: aprovado.

Decisão:

A V1 inicia com quatro modelos femininas de referência, entre 25 e 28 anos:

- pele clara, cabelo loiro;
- pele clara, cabelo preto;
- pele clara, cabelo ruivo;
- pele negra, cabelo escuro.

Consequência:

A mesma biblioteca será usada por Detalhe no Corpo e Na Modelo.

## ADR-007 - SceneTemplate pertence ao Instagramável

Status: aprovado.

Decisão:

`SceneTemplate` será usado oficialmente para o modo `INSTAGRAM`, exibido como Instagramável.

Consequência:

Cenários serão cadastráveis pelo SuperAdmin e selecionáveis pelo usuário no fluxo Instagramável.

## ADR-008 - MODEL será exibido como Na Modelo

Status: aprovado.

Decisão:

O modo interno `MODEL` será exibido como Na Modelo.

Consequência:

O modo usa `ModelReference` e deve escolher corpo inteiro ou 3/4 conforme a legibilidade da peça.

## ADR-009 - Um crédito por geração na V1

Status: aprovado.

Decisão:

Na V1, toda geração consome 1 crédito, independentemente do modo.

Consequência:

Não haverá multiplicador de crédito por complexidade ou modo nesta versão.

## ADR-010 - Validação visual humana antes de produção

Status: aprovado.

Decisão:

Novos modos e novas regras de categoria devem passar por validação visual humana antes de produção.

Consequência:

Testes automatizados são obrigatórios, mas não substituem aprovação visual dos resultados.

## ADR-011 - Execução multiagente controlada

Status: aprovado.

Decisão:

O MARIED STUDIO poderá ser desenvolvido por múltiplos agentes independentes, inclusive em paralelo, desde que cada agente trabalhe em um workstream com escopo fechado, dependências explícitas e ownership de arquivos.

A execução paralela só é permitida quando:
- a tarefa está `READY`;
- dependências obrigatórias já foram concluídas;
- agentes não disputam simultaneamente o mesmo arquivo compartilhado;
- arquivos permitidos/proibidos estão definidos;
- critérios de aceite e testes estão documentados.

## ADR-012 - Ownership de arquivos por workstream

Status: aprovado.

Toda tarefa deve declarar:
- owner/workstream;
- arquivos permitidos;
- arquivos proibidos;
- shared files;
- necessidade de lock/coordenação.

Arquivos compartilhados como `apps/ai/services/prompt_engine.py`, `apps/studio/models.py`, `settings.py`, `urls.py` e contratos centrais de API não podem ser editados simultaneamente por agentes diferentes sem coordenação.

## ADR-013 - Dependências explícitas entre tarefas

Status: aprovado.

Status oficiais:
- `BLOCKED`
- `READY`
- `IN_PROGRESS`
- `REVIEW`
- `VALIDATED`

Tarefas devem declarar `DEPENDS_ON` e `BLOCKS`.

Exemplo:

```text
AI-001 ModelReference
    ├── AI-002 BODY_DETAIL
    └── AI-004 MODEL
```

## ADR-014 - Execução por task files

Status: aprovado.

Tarefas do Codex devem ser descritas em `docs/tasks/` com escopo pequeno e verificável.

Exemplos:
- `BILLING-001.md`
- `AI-001-model-reference.md`
- `AI-002-body-detail.md`
- `AI-003-instagram.md`
- `AI-004-on-model.md`
- `FRONT-001.md`
- `ADMIN-001.md`
- `QA-001.md`
