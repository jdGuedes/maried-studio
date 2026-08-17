# MARIED STUDIO - Documento do Projeto

Este documento registra o estado atual do projeto, o que ja foi construido ate agora e as regras que devem ser seguidas antes de qualquer nova alteracao. Ele deve ser usado como referencia para preservar a logica do sistema.

## 1. Objetivo do sistema

O MARIED STUDIO e um estudio digital para criacao profissional de imagens de semijoias.

O fluxo principal do MVP e:

1. O usuario cadastra uma peca com imagem original.
2. O usuario escolhe um modo de geracao.
3. O usuario escolhe um estilo/template fotografico quando aplicavel.
4. O sistema reserva 1 credito.
5. O sistema gera 1 imagem usando o servico de IA.
6. Em caso de sucesso, o credito reservado e consumido.
7. Em caso de falha tecnica, o credito reservado e devolvido.
8. O resultado fica registrado no historico de geracoes.

Regra central do MVP:

```text
1 produto + 1 geracao = 1 imagem = 1 credito
```

## 2. Stack atual

Backend:

- Python 3.12+
- Django
- Django REST Framework
- SQLite em desenvolvimento
- PostgreSQL preparado via `DATABASE_URL`
- Integracao OpenAI encapsulada em `apps/ai/providers/openai.py`

Frontend:

- Next.js
- React
- TypeScript
- Tailwind CSS
- `lucide-react` para icones
- `motion` para animacoes

## 3. Estrutura principal

Raiz do projeto:

- `manage.py`: entrada do Django.
- `requirements.txt`: dependencias Python.
- `.env` e `.env.example`: configuracoes de ambiente.
- `db.sqlite3`: banco local de desenvolvimento.
- `media/`: arquivos de upload e imagens geradas.
- `frontend/`: aplicacao Next.js.
- `apps/`: apps Django.
- `config/`: configuracao principal do Django.
- `jewelry_ai_studio_backend_backup/`: backup do backend anterior.

Apps Django:

- `apps/accounts`: usuarios, perfil e dados de organizacao no perfil.
- `apps/organizations`: organizacoes/empresas.
- `apps/products`: cadastro e listagem de pecas.
- `apps/studio`: templates fotograficos, geracoes e dashboard.
- `apps/credits`: carteira, transacoes, reservas e consumo de creditos.
- `apps/ai`: prompt engine e provider de IA.
- `apps/audit`: registros de auditoria.
- `apps/billing`: modelos iniciais relacionados a cobranca.
- `apps/common`: modelos e utilitarios comuns.

Frontend principal:

- `frontend/src/app/page.tsx`: pagina inicial com dashboard.
- `frontend/src/app/criar/page.tsx`: fluxo de criacao de imagem.
- `frontend/src/app/pecas/page.tsx`: tela de pecas cadastradas.
- `frontend/src/app/perfil/page.tsx`: tela de perfil.
- `frontend/src/components/layout/app-shell.tsx`: layout principal com menu, saldo e perfil.
- `frontend/src/components/dashboard/dashboard-home.tsx`: dashboard da home.
- `frontend/src/providers/profile-provider.tsx`: estado global do perfil.
- `frontend/src/providers/credit-wallet-provider.tsx`: estado global da carteira de creditos.
- `frontend/src/lib/api.ts`: funcoes principais de produtos, templates e geracoes.
- `frontend/src/lib/dashboard.ts`: chamada da API do dashboard.
- `frontend/src/lib/profile.ts`: chamadas da API de perfil.
- `frontend/src/lib/credit-wallet.ts`: chamadas da API de creditos.

## 4. Endpoints principais atuais

Configurados em `config/urls.py`:

- `/api/accounts/`
- `/api/products/`
- `/api/studio/`
- `/api/credits/`
- `/admin/`

Studio:

- `GET /api/studio/dashboard/`
- `GET /api/studio/templates/`
- `POST /api/studio/generations/`
- `GET /api/studio/generations/<uuid>/`

Produtos:

- `GET /api/products/`
- `POST /api/products/`

Perfil:

- `GET /api/accounts/me/`
- `PATCH /api/accounts/me/`

Creditos:

- endpoint de carteira usado pelo frontend em `frontend/src/lib/credit-wallet.ts`.

## 5. Passo a passo ja criado ate agora

### 5.1 Base do backend

1. Foi criada a estrutura Django com apps separados por dominio.
2. Foram criados modelos para usuarios, organizacoes, produtos, studio, creditos, auditoria e billing.
3. Foram criadas migrations iniciais para os apps principais.
4. Foi configurado o uso de SQLite em desenvolvimento.
5. Foi preparada a compatibilidade com PostgreSQL via `DATABASE_URL`.
6. Foi configurado o uso de media local em desenvolvimento.

### 5.2 Organizacao e usuarios

1. Usuario possui vinculo com uma organizacao.
2. O perfil retorna dados do usuario, papel, organizacao e status de superusuario.
3. O frontend carrega o perfil globalmente pelo `ProfileProvider`.
4. O nome exibido, iniciais, organizacao e permissao de SuperAdmin sao derivados no provider.
5. A tela de perfil permite consultar e atualizar dados permitidos.
6. Apenas proprietario pode alterar o nome da empresa.

### 5.3 Pecas/produtos

1. O usuario pode cadastrar uma peca.
2. O cadastro envia nome, categoria, status e imagem original.
3. O upload usa `multipart/form-data`.
4. O frontend nao define manualmente `Content-Type` no upload, deixando o navegador gerar o boundary.
5. O dashboard conta apenas produtos com status `ACTIVE`.
6. Produtos arquivados continuam preservados no banco, mas nao entram na contagem principal do dashboard.

### 5.4 Studio e geracao de imagens

1. O sistema possui templates fotograficos por categoria e modo.
2. O frontend busca templates por categoria e modo.
3. A geracao recebe `product_id`, `mode`, `scene_template_id` e `idempotency_key`.
4. O `idempotency_key` evita duplicidade por clique duplo ou retry.
5. A geracao registra prompt final e snapshot de configuracao.
6. O processamento de IA esta centralizado em servicos do backend.
7. A integracao OpenAI esta encapsulada em `apps/ai/providers/openai.py`.
8. O prompt engine fica em `apps/ai/services/prompt_engine.py`.

### 5.5 Creditos

1. A carteira de creditos pertence a organizacao.
2. O saldo e carregado globalmente pelo `CreditWalletProvider`.
3. Antes de gerar imagem, o sistema reserva credito.
4. Em sucesso, o credito e consumido.
5. Em falha tecnica, o credito e devolvido.
6. A UI pode atualizar rapidamente o saldo apos uma geracao usando o retorno da API.
7. O dashboard tambem retorna `available_credits`.

### 5.6 Dashboard

1. A pagina inicial renderiza `DashboardHome` dentro de `AppShell`.
2. O dashboard busca dados em `GET /api/studio/dashboard/`.
3. Por padrao, o backend usa o mes atual como periodo.
4. O dashboard possui filtros independentes para criacoes e pecas.
5. Os parametros aceitos para criacoes sao:
   - `generation_start_date`
   - `generation_end_date`
6. Os parametros aceitos para pecas sao:
   - `product_start_date`
   - `product_end_date`
7. Se apenas uma data for enviada, o backend retorna erro.
8. Se a data inicial for maior que a final, o backend retorna erro.
9. Criacoes contam apenas geracoes com status `COMPLETED`.
10. Geracoes `FAILED`, `CANCELLED` e `PROCESSING` nao entram na contagem.
11. As ultimas criacoes acompanham o mesmo periodo do card "Criacoes".
12. O dashboard retorna ate 8 geracoes recentes.
13. A interface exibe no maximo 4 geracoes recentes na home.

### 5.7 Layout e navegacao

1. `AppShell` concentra sidebar desktop, header mobile e navegacao mobile.
2. O saldo de creditos aparece no desktop e no mobile.
3. O perfil aparece no rodape da sidebar desktop.
4. O menu possui links para:
   - Inicio
   - Criar imagem
   - Minhas criacoes
   - Minhas pecas
   - Creditos
5. A rota `/criacoes` ainda nao existe no frontend.
6. A opcao "Creditos" no menu ainda nao possui rota real.
7. O botao "Sair" ainda nao possui acao real implementada.

### 5.8 Telas frontend existentes

1. Home/dashboard: `/`
2. Criacao de imagem: `/criar`
3. Pecas: `/pecas`
4. Perfil: `/perfil`

Rotas citadas pela UI mas ainda pendentes:

1. `/criacoes`
2. rota/tela de creditos

## 6. Regras para preservar a logica do sistema

Estas regras devem ser seguidas em qualquer proxima alteracao.

### 6.1 Regras gerais

1. Nao alterar regras de negocio sem pedido explicito.
2. Nao mudar nomes de campos da API sem atualizar frontend, serializers e documentacao.
3. Nao remover validacoes existentes.
4. Nao remover filtros de organizacao das queries.
5. Nao misturar dados entre organizacoes.
6. Nao contar registros arquivados como ativos.
7. Nao alterar status validos sem revisar todos os fluxos dependentes.
8. Nao refatorar arquivos grandes sem necessidade direta.
9. Nao trocar bibliotecas ou arquitetura sem motivo claro.
10. Antes de editar, entender o fluxo completo impactado.

### 6.2 Regras de creditos

1. Manter a regra de 1 imagem gerada para 1 credito.
2. Nao consumir credito antes de existir uma reserva valida.
3. Nao perder credito do usuario em falha tecnica.
4. Nao permitir saldo negativo por mudanca de frontend.
5. Nao confiar apenas no frontend para regras de credito.
6. Toda mudanca em geracao deve considerar reserva, consumo, devolucao e idempotencia.
7. Nao remover ou ignorar `idempotency_key`.

### 6.3 Regras de geracao

1. Nao criar geracoes duplicadas para o mesmo clique/retry.
2. Nao alterar o contrato de `createGeneration` sem revisar o backend.
3. Nao mudar modos de geracao sem revisar templates, prompt engine e serializers.
4. Nao remover registro de prompt final e snapshot.
5. Nao expor detalhes sensiveis da IA no frontend.
6. Nao mover a chamada de IA para o frontend.

### 6.4 Regras de dashboard

1. O periodo padrao do dashboard deve continuar sendo o mes atual, salvo pedido contrario.
2. Criacoes no dashboard devem continuar contando apenas `COMPLETED`.
3. Pecas no dashboard devem continuar contando apenas `ACTIVE`.
4. Filtros de criacoes e pecas devem continuar independentes.
5. Nao alterar nomes dos query params sem compatibilidade.
6. Ao mexer no filtro de datas, preservar validacao de data inicial e final.
7. As ultimas criacoes devem continuar respeitando o periodo de criacoes.

### 6.5 Regras de perfil e organizacao

1. Perfil deve carregar com `credentials: "include"`.
2. Alteracoes protegidas devem manter CSRF.
3. Somente `OWNER` pode alterar nome da organizacao.
4. `is_superuser` e indicador global, nao substitui automaticamente regras de organizacao.
5. Nao exibir dados de outra organizacao.

### 6.6 Regras de frontend

1. Manter chamadas autenticadas com `credentials: "include"`.
2. Manter CSRF em operacoes `POST`, `PATCH`, `PUT` e `DELETE` quando exigido.
3. Nao definir `Content-Type` manualmente em upload `FormData`.
4. Manter o estado global de perfil no `ProfileProvider`.
5. Manter o estado global de creditos no `CreditWalletProvider`.
6. Evitar duplicar logica de API em componentes.
7. Preferir novas funcoes em `frontend/src/lib/` para chamadas HTTP.
8. Preservar o padrao visual existente do MARIED STUDIO.
9. Usar icones de `lucide-react` quando houver icone adequado.
10. Nao criar telas de marketing quando a necessidade for uma ferramenta operacional.

### 6.7 Regras de backend

1. Validacoes de negocio devem ficar no backend.
2. Serializers devem manter contratos claros com o frontend.
3. Views devem filtrar por usuario/organizacao.
4. Services devem concentrar regras complexas.
5. Nao capturar excecoes de forma silenciosa quando isso esconder erro de negocio.
6. Nao alterar migrations antigas manualmente depois que ja foram aplicadas, salvo decisao explicita.
7. Criar nova migration para mudancas de schema.

## 7. Pontos pendentes conhecidos

1. Criar rota/tela `/criacoes`.
2. Criar fluxo/tela de creditos.
3. Implementar acao real para "Adicionar creditos".
4. Implementar acao real para item "Creditos" do menu.
5. Implementar acao real para "Sair".
6. Revisar o comportamento do botao "Aplicar" no filtro personalizado do dashboard, pois hoje a recarga acontece quando as datas mudam.
7. Atualizar comentario em `profile-provider.tsx` que diz que `is_superuser` sera acrescentado no futuro, pois o campo ja existe no serializer.
8. Considerar mover processamento de IA para fila/worker em uma etapa futura.
9. Considerar storage externo como S3/Supabase em producao.
10. Considerar autenticacao por token/JWT em etapa futura, se necessario.

## 8. Como rodar localmente

Backend:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Seed inicial do studio:

```powershell
python manage.py seed_studio
```

## 9. Checklist antes de qualquer nova alteracao

Antes de alterar codigo, seguir este checklist:

1. Identificar qual fluxo sera impactado.
2. Ler os arquivos diretamente relacionados ao fluxo.
3. Confirmar se a mudanca e visual, de API ou de regra de negocio.
4. Se for regra de negocio, pedir confirmacao quando nao estiver explicito.
5. Preservar contratos existentes entre frontend e backend.
6. Fazer alteracao pequena e localizada.
7. Rodar verificacao possivel:
   - lint/build no frontend quando alterar React/TypeScript.
   - testes ou `python manage.py check` quando alterar Django.
8. Informar claramente o que foi alterado.
9. Informar o que nao foi possivel verificar.

## 10. Observacao importante

Este documento descreve o estado observado do projeto neste momento. Quando novas funcionalidades forem criadas, este documento deve ser atualizado junto com a mudanca para continuar servindo como fonte de referencia.
