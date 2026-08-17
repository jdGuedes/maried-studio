# AGENTS.md - MARIED STUDIO

Manual operacional obrigatório para agentes trabalhando no projeto MARIED STUDIO.

## Leitura obrigatória antes de alterar código

Antes de qualquer implementação, leia nesta ordem:

1. `PRD.md`
2. `SPEC.md`
3. `ADR.md`
4. `PLAN.md`
5. `PROJECT_STATE.md`
6. Código real do projeto

Não implemente com base apenas na documentação. A documentação define a intenção; o código real define o estado atual.

## Arquivos sincronizados

Este diretório pode conter arquivos em `sources/` vindos de um espelho do ChatGPT Project.

- Trate tudo em `sources/` como material de referência somente leitura.
- Não edite, renomeie, mova ou delete arquivos em `sources/`.
- O espelho pode estar incompleto.

## Princípios de trabalho

- Preserve compatibilidade com dados e migrations existentes.
- Não apague migrations.
- Não refatore arquitetura sem necessidade direta da tarefa.
- Não altere regras de crédito sem autorização explícita.
- Não altere isolamento por organização.
- Antes de concluir, execute validações disponíveis no projeto.
- Se uma regra de negócio estiver ambígua, pare e peça decisão.

## Modos oficiais de geração

Os valores internos do sistema devem ser preservados:

| Valor interno | Nome exibido |
| --- | --- |
| `STILL` | Still |
| `BODY_DETAIL` | Detalhe no Corpo |
| `INSTAGRAM` | Instagramável |
| `MODEL` | Na Modelo |

Não renomeie os valores internos para evitar migrations e quebras de compatibilidade.

## Proteção do PromptEngine

O arquivo `apps/ai/services/prompt_engine.py` já contém suporte conceitual aos modos `STILL`, `BODY_DETAIL`, `INSTAGRAM` e `MODEL`.

Os prompts abaixo são ativos validados do produto:

- `STILL`
- regra especializada `("EARRING", "BODY_DETAIL")`

É proibido reescrever, resumir, otimizar, reorganizar ou "melhorar" esses prompts sem autorização explícita do responsável pelo produto.

Mudanças necessárias para `ModelReference` devem preservar integralmente as regras validadas de:

- fidelidade da joia;
- escala real;
- anatomia correta;
- posicionamento;
- composição;
- qualidade fotográfica;
- protagonismo da peça.

## ModelReference

`ModelReference` é uma entidade planejada e diferente de `SceneTemplate`.

Ela será usada por:

- `BODY_DETAIL` / Detalhe no Corpo;
- `MODEL` / Na Modelo.

Biblioteca inicial:

| Código | Descrição |
| --- | --- |
| `MODEL_01` | Mulher de 25 a 28 anos, pele clara, cabelo loiro |
| `MODEL_02` | Mulher de 25 a 28 anos, pele clara, cabelo preto |
| `MODEL_03` | Mulher de 25 a 28 anos, pele clara, cabelo ruivo |
| `MODEL_04` | Mulher de 25 a 28 anos, pele negra, cabelo escuro |

Campos sugeridos:

- `id`
- `name`
- `slug`
- `description`
- `prompt_instruction`
- `preview_image`
- `is_active`
- `sort_order`

## BODY_DETAIL / Detalhe no Corpo

`BODY_DETAIL` permanece validado como Detalhe no Corpo. Não transformar em modo genérico de close.

A mudança planejada é substituir a escolha de direção visual por escolha de `ModelReference`.

O sistema deve mapear automaticamente a área corporal pela categoria:

| Categoria | Área corporal |
| --- | --- |
| `EARRING` | orelha e lateral do rosto |
| `NECKLACE` | pescoço e colo |
| `RING` | mão e dedos |
| `BRACELET` | pulso e braço |
| `ANKLET` | tornozelo, pé e perna |

Regra importante: a usuária escolhe a modelo; o sistema escolhe automaticamente a área corporal.

## INSTAGRAM / Instagramável

`INSTAGRAM` usa `SceneTemplate`.

`SceneTemplate` já é compatível com a arquitetura atual do `PromptEngine` para cenários comerciais. A implementação deve permitir cenários cadastráveis e administráveis pelo SuperAdmin.

## MODEL / Na Modelo

`MODEL` é exibido como Na Modelo.

Esse modo usa `ModelReference` e deve gerar a joia aplicada em uma modelo, usando corpo inteiro ou enquadramento 3/4 conforme a legibilidade da peça.

## Créditos V1

Regra oficial da V1:

```text
1 geração = 1 crédito
```

Essa regra vale para todos os modos:

- Still;
- Detalhe no Corpo;
- Instagramável;
- Na Modelo.

## Relatório final obrigatório

Ao concluir uma tarefa, informe:

- arquivos alterados;
- validações executadas;
- resultado dos testes;
- riscos ou pendências;
- decisões que exigem validação humana.

## Modelo de execução multiagente

O MARIED STUDIO admite múltiplos agentes trabalhando de forma independente, inclusive em paralelo, desde que o trabalho esteja dividido em tarefas formais.

### Status oficiais de tarefa

- `BLOCKED`: dependência não concluída.
- `READY`: pode ser iniciada.
- `IN_PROGRESS`: agente trabalhando.
- `REVIEW`: implementação concluída aguardando validação.
- `VALIDATED`: critérios de aceite cumpridos.

Um agente não deve iniciar uma tarefa `BLOCKED`.

### Workstreams oficiais

- `FOUNDATION`: ProfileProvider, contratos básicos e infraestrutura compartilhada.
- `BILLING`: Plan, Subscription, SubscriptionService e ciclo comercial.
- `BODY_DETAIL`: Detalhe no Corpo e regras corporais.
- `INSTAGRAMABLE`: SceneTemplate e cenários Instagramáveis.
- `ON_MODEL`: modo interno `MODEL`, exibido como Na Modelo.
- `FRONTEND_INTEGRATION`: integração de telas após contratos do backend.
- `SUPERADMIN`: administração global.
- `TESTS_QA`: testes de regressão, integração e validação técnica.

### Regra de independência

Agentes podem trabalhar em paralelo apenas quando:
1. as tarefas não dependem uma da outra;
2. ownership de arquivos não se sobrepõe;
3. não existe lock ativo em arquivo compartilhado;
4. contratos usados pela tarefa já estão estáveis;
5. cada agente respeita o escopo do task file.

### Ownership

Toda tarefa deve listar:
- arquivos permitidos;
- arquivos proibidos;
- arquivos compartilhados;
- lock necessário.

O agente não deve editar arquivos fora do escopo sem registrar a necessidade e pedir coordenação.

### Arquivos compartilhados de integração controlada

Tratar como shared files, salvo regra mais específica da tarefa:

```text
apps/ai/services/prompt_engine.py
apps/studio/models.py
config/settings.py ou equivalente
config/urls.py ou equivalente
serializers/URLs centrais que alterem contratos
frontend/src/app/layout.tsx
frontend/src/components/layout/app-shell.tsx
```

Dois agentes não devem alterar simultaneamente o mesmo shared file sem lock/coordenação.

### Dependências principais dos modos

```text
AI-001 ModelReference
   ├── bloqueia AI-002 BODY_DETAIL
   └── bloqueia AI-004 ON_MODEL

AI-003 INSTAGRAMABLE
   └── pode avançar em paralelo quando não disputar shared files

FRONTEND_INTEGRATION
   └── depende dos contratos/API dos modos expostos
```

### Protocolo de lock

Se a tarefa precisar alterar shared file:
1. marcar `LOCK_REQUIRED: true`;
2. verificar conflito;
3. se houver conflito, não editar;
4. aguardar integração ou dividir a alteração;
5. liberar o lock lógico após integração.

### Não ampliar escopo

O agente não deve aproveitar uma tarefa para:
- refatorar módulos não relacionados;
- renomear entidades;
- alterar arquitetura;
- limpar arquivos compartilhados;
- mudar regras comerciais;
- modificar prompts validados.

### Uso obrigatório de task files

Preferir:

```text
Execute docs/tasks/AI-002-body-detail.md
```

em vez de instruções amplas.

O task file é o contrato operacional da tarefa.
