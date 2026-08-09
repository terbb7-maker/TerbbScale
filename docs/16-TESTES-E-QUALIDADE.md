# Testes e qualidade

## 1. Objetivo

Provar regras críticas, isolamento, idempotência e comportamento sob falha. Cobertura numérica isolada não substitui cenários de risco.

## 2. Pirâmide

### Unitários

- cálculo de agenda;
- timezones e horário de verão;
- estratégias de mídia;
- sequência independente por conta, limite sem repetição por conta e decks aleatórios completos/determinísticos por ciclo;
- state machines;
- classificação de erros;
- backoff;
- fórmula de métricas;
- janelas Hoje/Ontem/Mês no timezone do usuário, datas inclusivas do período personalizado e limite de 366 dias;
- filtro por data de publicação usando somente o snapshot mais recente de cada mídia/métrica, com plano indexado e sem varrer todo o histórico;
- policies/RBAC;
- sanitização.

### Integração

- repositories com PostgreSQL real de teste;
- RLS/tenant isolation;
- Redis e locks;
- upload/storage;
- outbox;
- migrations;
- adapter Meta com servidor simulado.

### Contrato

- schemas OpenAPI;
- respostas esperadas do adapter;
- compatibilidade de versões;
- payloads de webhook quando usados.

### End-to-end

- cadastro pendente e aprovação;
- login/suspensão;
- configurar App e conectar conta de teste;
- upload/processamento;
- campanha/preview/ativação;
- execução/retry/log;
- dashboard/WebSocket;
- cancelamento/exclusão.

## 3. Cenários críticos

1. Dois workers reservam o mesmo job.
2. Meta publica, mas o worker cai antes de atualizar o banco.
3. Retry recebe novamente o mesmo job.
4. Token expira entre container e publish.
5. Usuário tenta usar mídia/conta de outro tenant.
6. Campanha é editada enquanto scheduler planeja.
7. Horário cai em transição de DST.
8. 429 contém `Retry-After`.
9. Redis perde todo estado.
10. Usuário é suspenso com jobs futuros.
11. Mídia é removida durante campanha.
12. Métrica não existe para o formato.
13. Jobs da mesma conta ficam devidos juntos e tentam ultrapassar a posição planejada.
14. Lock de publicação da conta já está ocupado por outro worker.

## 4. Testes da Meta

- A maioria usa fake server reproduzível.
- Sandbox/contas de teste validam contratos reais.
- Nenhum teste automatizado publica em conta de produção.
- Testes reais têm marcação, limites e cleanup.
- Respostas reais sanitizadas podem gerar fixtures sem tokens/PII.

## 5. Segurança

- autorização horizontal/vertical;
- OAuth state/replay;
- CSRF/CORS;
- JWT inválido/expirado/audience errada;
- upload disfarçado;
- path traversal;
- SSRF se entrada por URL for adicionada;
- redaction de logs;
- configuração de logging da API, scheduler e Celery não registra URLs de transporte com tokens;
- rate limit;
- secret rotation.

## 6. Frontend

- componentes e validações;
- acessibilidade automatizada e manual;
- keyboard-only;
- responsive em larguras alvo;
- estados vazio/erro/loading/parcial;
- campanhas em browsers suportados;
- regressão visual dos fluxos críticos;
- WebSocket reconnection/fallback.
- classificação de códigos/subcódigos oficiais de token, checkpoint, permissão, restrição, rate limit e falhas transitórias;
- inferência de possível suspensão somente após repetição e sem classificar erro de mídia como problema da conta;
- indisponibilidade da Meta não remove bloqueio anterior; sucesso oficial recupera a conta;
- scheduler não despacha conta bloqueada e o publisher reagenda sem consumir tentativa.

## 7. Performance

- benchmarks do planner;
- queries do dashboard;
- upload concorrente;
- fila e worker com Meta simulada;
- soak test;
- failure storm;
- WebSocket concurrency.

## 8. Quality gates propostos

Antes de merge:

- lint/format;
- type checking estrito;
- unit/integration tests;
- migration check;
- OpenAPI diff;
- dependency/secret scan;
- frontend build;
- acessibilidade básica.

Antes de release:

- E2E;
- backup/restore quando afetado;
- migration forward/rollback strategy;
- teste de idempotência;
- smoke em staging;
- aprovação de segurança para áreas críticas.

## 9. Cobertura

Proposta:

- serviços críticos e regras de domínio: branch coverage mínima de 90%;
- conjunto geral: meta inicial de 80%;
- não excluir arquivo crítico apenas para elevar número.

Os limiares finais são decisão de engenharia após o esqueleto.

## 10. Definição de pronto

Uma função está pronta quando:

- atende critério de aceite;
- tem autorização e tenant scope;
- trata erro/loading;
- possui logs/métricas;
- tem testes proporcionais ao risco;
- está documentada no OpenAPI;
- não expõe segredo;
- foi validada responsivamente quando há UI.
# Cobertura de Proxy Manager

Testar validação de host/protocolo/porta, cifragem e escaping de credenciais, isolamento de tenant, pool por campanha e ausência de fallback direto quando a campanha exige proxy. Cobrir parser da entrada `host:porta:usuário:senha`, limite de 500 linhas, rotação por rodada/a cada X rodadas, cooldown, fallback para outra proxy e isolamento de falhas de teste para que um proxy inválido resulte em status offline, nunca em erro 500. Cobrir também os limites de 200 IDs, o isolamento das remoções em massa, a classificação de falha DNS, o limiar do monitor periódico e o limite de concorrência dos testes em lote.

# Cobertura do ranking mensal

Testar limites do mês no horário de Brasília, dezembro/virada do ano, rejeição de mês futuro, fórmula bruta do score, seleção do último snapshot por mídia, desempate determinístico, inclusão da posição do usuário atual e ausência de e-mail no contrato. Validar a consulta com `EXPLAIN` e os índices parciais de jobs/insights, além de lint, TypeScript, build de produção e layout responsivo.

# Cobertura da distribuição de mídias

Testar múltiplas contas por mais de um ciclo: sequencial avança individualmente, aleatório usa todas as mídias antes de repetir em cada conta, a mesma seed reproduz o plano, a fronteira entre ciclos não repete imediatamente e `allow_media_reuse=false` limita cada conta ao tamanho do conjunto. No publisher, testar predecessor pendente, lock por conta ocupado e liberação para o próximo job, sem incrementar tentativa quando a execução apenas precisa aguardar.
