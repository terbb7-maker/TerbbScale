# Registro de decisões

Este documento registra decisões aceitas e evita que escolhas sejam perdidas em conversas.

## Formato

```text
ID:
Data:
Status: proposta | aceita | substituída
Decisão:
Contexto:
Consequências:
Substitui:
Aprovada por:
```

## ADR-000 — Somente documentação nesta fase

- **Data:** 31 de julho de 2026
- **Status:** aceita
- **Decisão:** criar a especificação em Markdown e impedir qualquer implementação até aprovação explícita do proprietário.
- **Contexto:** o proprietário quer ler e aprovar todo o entendimento antes do código.
- **Consequências:** o repositório permanece sem backend, frontend, migrations e infraestrutura; `AGENTS.md` e o gate regulam futuras ações.
- **Aprovada por:** instrução original do proprietário.

## ADR-001 — Integração oficial com Instagram Login

- **Data:** 31 de julho de 2026
- **Status:** aceita
- **Decisão:** usar exclusivamente Instagram Platform API com Instagram Login, sem Facebook Login ou automação não oficial.
- **Consequências:** somente contas/capacidades suportadas oficialmente; alterações da Meta podem reduzir funções.
- **Aprovada por:** requisito original do proprietário.

## ADR-002 — Backend Python e stack base

- **Data:** 31 de julho de 2026
- **Status:** aceita como requisito
- **Decisão:** backend Python 3.13, FastAPI, SQLAlchemy 2, Alembic, AsyncIO, APScheduler, httpx e Pydantic V2; Supabase e Redis.
- **Consequências:** compatibilidade concreta das versões deverá ser comprovada antes de congelar dependências.
- **Aprovada por:** requisito original do proprietário.

## ADR-003 — Worker independente

- **Data:** 31 de julho de 2026
- **Status:** aceita como requisito
- **Decisão:** execução de publicação ocorre fora da API principal.
- **Consequências:** jobs duráveis, fila, idempotência, observabilidade e deploy independente.
- **Aprovada por:** requisito original do proprietário.

## ADR-004 — Recomendações adotadas como baseline

- **Data:** 31 de julho de 2026
- **Status:** aceita
- **Decisão:** adotar as opções A recomendadas de `DEC-001` a `DEC-017`, `DEC-019` e `DEC-020`; em `DEC-018`, usar 7 dias para recuperação de mídia, 90 dias para logs detalhados, 12 meses para auditoria e até 30 dias para exclusão de usuário.
- **Contexto:** o proprietário aprovou o projeto e concedeu autorização total de implementação sem selecionar alternativas.
- **Consequências:** a implementação pode avançar sem novas perguntas para essas escolhas; mudanças futuras exigem ADR.
- **Aprovada por:** delegação explícita do proprietário.

## ADR-005 — Implementação completa autorizada

- **Data:** 31 de julho de 2026
- **Status:** aceita
- **Decisão:** iniciar os marcos do PostX e operar o workspace, a VPS `179.197.73.32` e o projeto Supabase `kctretlyslltvkfydoyy`.
- **Consequências:** código, migrations, serviços, testes e deploy estão autorizados; segredos continuam fora do versionamento e a integração Instagram continua exclusivamente oficial.
- **Aprovada por:** mensagem explícita do proprietário.
# ADR — Proxy Manager (31 de julho de 2026)

Decidido: proxies são opcionais e por usuário; credenciais usam o cofre AES-GCM existente; `ProxyManager` constrói clientes descartáveis; SOCKS5 é suportado por `socksio`; campanhas suportam conexão direta, por conta e específica.

# ADR — Rotação de Proxy por Conta (31 de julho de 2026)

**Status: substituída.** A configuração por conta foi removida da interface e substituída pela rotação exclusiva por campanha, conforme decisão posterior do proprietário.

## ADR-006 — Situação operacional das contas pela API oficial

- **Data:** 1º de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** monitorar contas em background pela API oficial, classificar erros documentados e representar suspensão genérica somente como inferência, pois Instagram Login não expõe um estado universal de suspensão/desafio.
- **Consequências:** a UI distingue confirmação de inferência; estados que exigem ação pausam/reagendam publicações; somente sucesso oficial remove bloqueios; nenhuma técnica não oficial será usada.
- **Aprovada por:** autorização explícita do proprietário para implementar tudo que fosse possível após análise da documentação da Meta.

## ADR-007 — Períodos das métricas de engajamento

- **Data:** 1º de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** classificar as métricas por publicações feitas Hoje, Ontem, no mês-calendário atual ou em intervalo personalizado inclusivo, sempre no timezone do usuário.
- **Consequências:** os valores representam o snapshot cumulativo mais recente das publicações selecionadas, não o momento exato em que cada interação ocorreu; consultas usam lookup lateral indexado e período personalizado máximo de 366 dias.
- **Aprovada por:** solicitação explícita do proprietário.

## ADR-008 — Identidade Terbb Scale e redução de densidade visual

- **Data:** 1º de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** adotar o nome público Terbb Scale e a marca roxa fornecida pelo proprietário; remover a landing page; usar login/cadastro como entrada; reduzir a dashboard a quatro KPIs principais, gráfico, engajamento e próximas publicações; adicionar remoção em massa de contas, mídias e proxies.
- **Consequências:** o nome técnico PostX pode permanecer em paths, containers e pacote interno; proxies usam remoção lógica para preservar o histórico; thumbnails são entregues por URLs privadas temporárias em lote.
- **Aprovada por:** solicitação explícita do proprietário.

## ADR-009 — Resiliência de DNS e saúde de proxies

- **Data:** 2 de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** fixar resolvers públicos nos containers Python, classificar falhas de transporte sem expor segredos, executar testes em lote com concorrência limitada e exigir três falhas periódicas consecutivas antes de retirar uma proxy saudável da rotação.
- **Contexto:** o resolver da VPS retornou `NXDOMAIN` incorreto para o endpoint oficial da Webshare e marcou 182 proxies de cinco usuários como offline.
- **Consequências:** testes manuais permanecem imediatos; falhas reais durante publicação continuam aplicando cooldown imediato; uma indisponibilidade transitória de DNS não derruba todo o pool em um único ciclo.
- **Aprovada por:** autorização explícita do proprietário após a auditoria.

## ADR-010 — Ranking mensal geral da comunidade

- **Data:** 3 de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** criar um único ranking mensal entre usuários ativos, usando a soma bruta de posts, views, curtidas, comentários, compartilhamentos, salvamentos e taxa de engajamento; exibir o detalhamento completo de cada participante.
- **Contexto:** o proprietário rejeitou rankings separados por categoria e determinou que views devem conservar seu maior peso natural.
- **Consequências:** o período segue o mês-calendário de Brasília; métricas representam o snapshot mais recente dos posts publicados no mês; o botão do ranking substitui o cartão promocional da sidebar; e-mails não são expostos.
- **Aprovada por:** esclarecimentos explícitos do proprietário.

## ADR-011 — Distribuição de mídia independente por conta

- **Data:** 4 de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** calcular as estratégias sequencial e aleatória sem reposição por conta; persistir a seed entre preview e ativação; gravar `plan_position`; e serializar a chamada externa dentro de cada conta/versão, mantendo paralelismo entre contas.
- **Contexto:** a distribuição global fazia contas sequenciais permanecerem na mesma mídia, permitia repetição aleatória antes de uma conta esgotar seu conjunto e deixava jobs posteriores ultrapassarem predecessores sob concorrência.
- **Consequências:** novas versões de campanha recebem o plano corrigido e auditável; jobs já materializados preservam sua mídia, mas passam a respeitar a ordem persistida após o backfill; replanejar mídia de campanha ativa exige operação explícita para não alterar publicação aprovada.
- **Aprovada por:** autorização explícita do proprietário após a auditoria.

## ADR-012 — Preparação local de sessão por cookies

- **Data:** 12 de agosto de 2026
- **Status:** aceita e implementada
- **Decisão:** manter o Instagram Login atual e adicionar uma alternativa em tela separada, apoiada por extensão Manifest V3, para importar localmente cookies do Instagram, preparar uma fila de sessões e iniciar o mesmo OAuth oficial.
- **Contexto:** o App da Meta ainda não está aprovado e o proprietário adiciona manualmente contas como testers; a sessão autenticada é necessária para revisar o convite antes do consentimento OAuth.
- **Consequências:** cookies nunca chegam ao backend/Supabase, somente `instagram.com` é aceito, a fila existe apenas em `chrome.storage.session`, o identificador é mascarado e Facebook/DoubleClick são ignorados. O aceite de convite, checkpoints e consentimentos continuam sujeitos à interface e às confirmações da Meta. Tokens, publicação e consultas permanecem exclusivamente na API oficial.
- **Aprovada por:** solicitação explícita do proprietário.
