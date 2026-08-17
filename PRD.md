# PRD.md - MARIED STUDIO

## Visão geral

MARIED STUDIO é uma plataforma para criação de imagens profissionais de semijoias com IA. O produto permite que marcas e lojas enviem fotos de peças e gerem imagens comerciais prontas para catálogo, redes sociais e apresentação ao cliente.

O foco da V1 é preservar a fidelidade da peça original, simplificar a experiência de geração e organizar os quatro modos oficiais de criação.

## Objetivos da V1

- Manter o modo Still preservado e validado.
- Manter o modo Detalhe no Corpo como `BODY_DETAIL`, preservando a validação existente, especialmente para brincos.
- Substituir direções visuais no Detalhe no Corpo por escolha de modelo.
- Criar a entidade `ModelReference` para modelos reutilizáveis.
- Usar `SceneTemplate` para cenários Instagramáveis cadastráveis.
- Exibir `MODEL` como Na Modelo, usando a mesma biblioteca de modelos.
- Padronizar a cobrança V1 como `1 geração = 1 crédito`.
- Proteger prompts já validados contra reescrita sem autorização.

## Usuários

### Cliente

Usuária que envia fotos de semijoias e cria imagens comerciais.

Principais necessidades:

- gerar imagens com fidelidade à peça;
- escolher modo de criação de forma simples;
- visualizar créditos disponíveis;
- criar variações com consistência;
- baixar ou reutilizar resultados.

### SuperAdmin

Usuário interno responsável por administração global.

Responsabilidades:

- gerenciar clientes e organizações;
- administrar planos, créditos e assinaturas;
- cadastrar e ativar cenários Instagramáveis;
- futuramente cadastrar e ordenar modelos de referência;
- validar resultados antes de produção.

## Modos oficiais de geração

| Valor interno | Nome exibido | Escolha adicional |
| --- | --- | --- |
| `STILL` | Still | Nenhuma |
| `BODY_DETAIL` | Detalhe no Corpo | `ModelReference` |
| `INSTAGRAM` | Instagramável | `SceneTemplate` |
| `MODEL` | Na Modelo | `ModelReference` |

Os valores internos devem ser mantidos.

## Still

Status: validado.

Comportamento esperado:

- gerar imagem limpa de produto;
- fundo branco;
- peça como protagonista;
- sem modelo;
- sem cenário;
- sem alterar pedras, formato, banho, textura, cravação, estrutura ou acabamento.

Não deve haver escolha adicional para Still na V1.

## Detalhe no Corpo

Status: validado para `EARRING` com `BODY_DETAIL`.

`BODY_DETAIL` permanece o modo oficial Detalhe no Corpo. Ele não deve ser renomeado nem transformado em um modo genérico de close.

Mudança planejada:

- remover as opções de direção visual `Elegante`, `Luxuoso`, `Editorial` e `Natural` desse modo;
- inserir escolha de `ModelReference`;
- mapear automaticamente a área corporal pela categoria.

Mapeamento oficial:

| Categoria | Área corporal |
| --- | --- |
| `EARRING` | orelha e lateral do rosto |
| `NECKLACE` | pescoço e colo |
| `RING` | mão e dedos |
| `BRACELET` | pulso e braço |
| `ANKLET` | tornozelo, pé e perna |

Exemplo de fluxo:

```text
Usuária envia brinco
Escolhe Detalhe no Corpo
Escolhe uma modelo
Sistema aplica automaticamente na orelha/lateral do rosto
Consome 1 crédito
```

## Instagramável

Status: planejado sobre base existente.

`INSTAGRAM` deve ser exibido como Instagramável.

Comportamento esperado:

- usuária escolhe um cenário;
- cenário vem de `SceneTemplate`;
- joia permanece protagonista;
- cenário é comercial, elegante e configurável;
- SuperAdmin pode cadastrar, editar, ordenar, ativar e desativar cenários.

`SceneTemplate` já é compatível com a arquitetura atual para Instagramável.

## Na Modelo

Status: planejado sobre base existente.

`MODEL` deve ser exibido como Na Modelo.

Comportamento esperado:

- usuária escolhe uma `ModelReference`;
- sistema aplica a joia na modelo;
- composição pode ser corpo inteiro ou 3/4;
- o enquadramento deve priorizar a legibilidade da peça;
- a peça deve preservar escala real e fidelidade visual.

## ModelReference

`ModelReference` é uma nova entidade planejada. Ela não substitui `SceneTemplate`.

Usos:

- Detalhe no Corpo;
- Na Modelo.

Biblioteca inicial:

| Código | Descrição |
| --- | --- |
| `MODEL_01` | Mulher de 25 a 28 anos, pele clara, cabelo loiro |
| `MODEL_02` | Mulher de 25 a 28 anos, pele clara, cabelo preto |
| `MODEL_03` | Mulher de 25 a 28 anos, pele clara, cabelo ruivo |
| `MODEL_04` | Mulher de 25 a 28 anos, pele negra, cabelo escuro |

## Créditos

Regra oficial V1:

```text
1 geração = 1 crédito
```

Essa regra vale igualmente para:

- Still;
- Detalhe no Corpo;
- Instagramável;
- Na Modelo.

Falhas de geração devem preservar ou estornar crédito conforme a política técnica existente de reserva, consumo, refund e idempotência.

## Critérios de aceite

- Os quatro modos aparecem com nomes corretos no frontend.
- Os valores internos continuam `STILL`, `BODY_DETAIL`, `INSTAGRAM` e `MODEL`.
- Still continua funcionando sem escolha adicional.
- Detalhe no Corpo permite escolher modelo e aplica área corporal automaticamente.
- Brinco em Detalhe no Corpo preserva o prompt validado.
- Instagramável lista cenários de `SceneTemplate`.
- Na Modelo lista modelos de `ModelReference`.
- Cada geração consome exatamente 1 crédito na V1.
- SuperAdmin consegue administrar cenários Instagramáveis.
- Testes cobrem regras principais antes de produção.

## Estratégia de entrega por frentes independentes

Para acelerar o produto sem perder controle, funcionalidades podem ser desenvolvidas por frentes independentes quando não houver dependência entre elas.

Exemplos:
- Billing pode evoluir em paralelo à biblioteca de modelos.
- Cenários Instagramáveis podem evoluir em paralelo ao Billing.
- Detalhe no Corpo e Na Modelo dependem da base `ModelReference`.
- Integração de frontend deve consumir contratos backend estabilizados.

Essa estratégia organiza a entrega, mas não altera regras de produto. A validação visual humana continua obrigatória antes de liberar novos modos em produção.
