# PROJECT_STATE.md - MARIED STUDIO

Estado do projeto para orientar o Codex e evitar confusão entre o que já está validado, implementado, em implementação e planejado.

## VALIDADO

### STILL

- Modo interno: `STILL`.
- Nome exibido: Still.
- Prompt validado.
- Fluxo conceitualmente validado.
- Não requer escolha adicional.
- Deve preservar fundo branco, fidelidade da peça e ausência de modelo/cenário.

Regra:

```text
Não reescrever, resumir ou otimizar o prompt Still sem autorização explícita.
```

### BODY_DETAIL para EARRING

- Modo interno: `BODY_DETAIL`.
- Nome exibido: Detalhe no Corpo.
- Regra especializada validada: `("EARRING", "BODY_DETAIL")`.
- Aplicação correta em orelha/lateral do rosto.
- Escala real e anatomia correta são requisitos validados.

Regra:

```text
Não reescrever, resumir ou otimizar EARRING + BODY_DETAIL sem autorização explícita.
```

## IMPLEMENTADO

### PromptEngine com quatro modos

O `PromptEngine` atual já contém os modos:

- `STILL`
- `BODY_DETAIL`
- `INSTAGRAM`
- `MODEL`

Observação:

Esses modos existem conceitualmente no motor, mas nem todos estão completos ou validados em produto.

### SceneTemplate compatível com Instagram

`SceneTemplate` já é compatível com a ideia de cenários para o modo `INSTAGRAM`.

Ainda falta estruturar cadastro, biblioteca oficial e fluxo completo no frontend, conforme o estado real do código.

## EM IMPLEMENTAÇÃO

### Reorganização oficial dos modos

Definição de produto aprovada:

| Interno | Exibição | Seleção |
| --- | --- | --- |
| `STILL` | Still | Nenhuma |
| `BODY_DETAIL` | Detalhe no Corpo | Modelo |
| `INSTAGRAM` | Instagramável | Cenário |
| `MODEL` | Na Modelo | Modelo |

### Documentação operacional para Codex

Este pacote documental define:

- PRD;
- SPEC;
- PLAN;
- ADR;
- AGENTS;
- PROJECT_STATE.

## PLANEJADO

### ModelReference

Criar nova entidade `ModelReference`.

Usada por:

- `BODY_DETAIL`;
- `MODEL`.

Biblioteca inicial:

- mulher de 25 a 28 anos, pele clara, cabelo loiro;
- mulher de 25 a 28 anos, pele clara, cabelo preto;
- mulher de 25 a 28 anos, pele clara, cabelo ruivo;
- mulher de 25 a 28 anos, pele negra, cabelo escuro.

### BODY_DETAIL para todas as categorias

Criar ou completar regras especializadas:

| Categoria | Área corporal |
| --- | --- |
| `EARRING` | orelha/lateral do rosto |
| `NECKLACE` | pescoço/colo |
| `RING` | mão/dedos |
| `BRACELET` | pulso/braço |
| `ANKLET` | tornozelo/pé/perna |

Mudança planejada:

- remover escolha de direção visual no `BODY_DETAIL`;
- adicionar escolha de `ModelReference`;
- calcular área corporal automaticamente por categoria.

### Instagramável

Planejado:

- exibir `INSTAGRAM` como Instagramável;
- usar `SceneTemplate`;
- permitir cenários cadastráveis pelo SuperAdmin;
- listar cenários ativos no frontend;
- validar visualmente antes de produção.

### Na Modelo

Planejado:

- exibir `MODEL` como Na Modelo;
- usar `ModelReference`;
- gerar corpo inteiro ou 3/4 conforme legibilidade da peça;
- criar regras por categoria;
- validar visualmente antes de produção.

### Frontend

Planejado:

- labels oficiais dos modos;
- seleção de modelo para Detalhe no Corpo;
- seleção de cenário para Instagramável;
- seleção de modelo para Na Modelo;
- Still sem seleção adicional;
- bloqueio de combinações inválidas.

### Créditos

Regra V1 planejada e aprovada:

```text
1 geração = 1 crédito
```

Aplica-se a todos os modos.

### Testes e validação

Planejado:

- testes de payload por modo;
- testes de consumo de crédito;
- testes de mapeamento corporal;
- testes de regressão dos prompts validados;
- validação visual humana antes de produção.

## ESTRATÉGIA MULTIAGENTE

Status: **APROVADA NA DOCUMENTAÇÃO**.

O projeto admite múltiplos agentes independentes, mas execução paralela exige:
- task file criado;
- status `READY`;
- dependências concluídas;
- ownership definido;
- shared files identificados;
- lock/coordenação quando necessário.

Workstreams aprovados:
- FOUNDATION
- BILLING
- BODY_DETAIL
- INSTAGRAMABLE
- ON_MODEL
- FRONTEND_INTEGRATION
- SUPERADMIN
- TESTS_QA

Dependências principais:
- `ModelReference` bloqueia integração de BODY_DETAIL e MODEL.
- Instagramável usa SceneTemplate e pode avançar independentemente quando não houver conflito de arquivos.

Estado operacional:
A estratégia está documentada. A execução paralela só deve começar quando task files e locks aplicáveis estiverem definidos.
