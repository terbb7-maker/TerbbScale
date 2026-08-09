# Observabilidade e operação

## 1. Três sinais

- **Logs:** eventos estruturados para investigação.
- **Métricas:** séries agregadas para tendência/alerta.
- **Traces:** caminho de uma ação entre API, fila, worker, banco e Meta.

Todos compartilham `request_id`, `correlation_id`, `job_id` e `campaign_id` quando aplicável, sem expor segredo.

## 2. Logs estruturados

Campos base:

- timestamp UTC;
- level;
- service/process;
- environment;
- event name;
- request/correlation ID;
- tenant ID pseudonimizado quando exportado;
- resource IDs;
- duration;
- outcome;
- error class.

Stack trace fica no agregador protegido, não na resposta da API.

## 3. Logs de publicação

Para cada tentativa:

- conta;
- campanha;
- mídia;
- horário previsto;
- início/fim;
- tempo total e por etapa;
- operação externa;
- HTTP status;
- ID externo;
- resposta sanitizada/truncada;
- classe de erro;
- retryable;
- próximo retry;
- estado final.

## 4. Métricas

### API

- request rate;
- taxa de 4xx/5xx;
- latência p50/p95/p99;
- conexões e pool;
- rate limits.

### Scheduler/fila

- último heartbeat;
- duração do ciclo;
- campanhas planejadas;
- jobs criados;
- backlog;
- idade do job mais antigo;
- lag;
- leases expirados;
- dead-letter.

### Worker/Meta

- taxa de publicação;
- sucesso/falha/retry;
- latência por etapa;
- 429/5xx;
- containers presos;
- tokens próximos do vencimento;
- limite consumido por conta/App.

### Dados/storage

- pool e queries lentas;
- tamanho das tabelas;
- falhas de migration;
- storage usado;
- upload/processamento;
- objetos órfãos.

## 5. Health endpoints

- **Liveness:** processo está vivo; não depende de toda infraestrutura.
- **Readiness:** pode receber trabalho; verifica dependências essenciais com orçamento curto.
- **Deep health:** somente admin/operador; apresenta banco, Redis, fila, scheduler, workers e storage.

Tokens, hostnames internos sensíveis e mensagens cruas nunca aparecem.

## 6. Painel de saúde

Estados por componente:

- operational;
- degraded;
- unavailable;
- unknown.

Mostrar último heartbeat, latência, backlog e incidente atual. “Operational” exige sinal recente, não ausência de erro.

## 7. Alertas iniciais

- scheduler sem heartbeat;
- fila envelhecendo;
- dead-letter acima do limiar;
- taxa de falha/429 elevada;
- banco/Redis indisponível;
- pool esgotado;
- tokens com falha de renovação;
- storage/processamento falhando;
- ausência anormal de workers;
- crescimento de erro administrativo.

Alertas devem ser acionáveis, deduplicados e ter runbook.

## 8. Runbooks exigidos antes de produção

- Meta indisponível/429;
- token massivamente inválido;
- scheduler parado;
- fila acumulada;
- Redis perdido;
- banco degradado;
- job possivelmente publicado sem confirmação local;
- vazamento/rotação de segredo;
- exclusão acidental de mídia;
- rollback de deploy/migration.

## 9. Dashboard em tempo real

Evento de publicação atualiza:

- contadores da campanha;
- feed de logs;
- notificação;
- próximas publicações;
- saúde da fila.

WebSocket é otimização. Se desconectado, a UI exibe estado e usa polling com cursor.

## 10. Retenção e acesso

Logs técnicos, logs de publicação e audit logs têm retenções e permissões diferentes. Suporte vê dados mínimos. Acesso global é auditado. Exportação não inclui segredos.
# Observabilidade de proxy

Os logs de publicação incluem modo, identificador/nome do proxy, IP público, latência conhecida e duração da requisição, sem credenciais. O status de saúde é atualizado pelo worker periódico e aparece no dashboard. O erro apresentado diferencia falha de DNS, timeout, conexão, autenticação e resposta HTTP, sem incluir credenciais. O monitor exige três falhas consecutivas antes de rebaixar uma proxy saudável; testes manuais continuam imediatos.

Cada tentativa também registra a proxy selecionada, motivo de rotação e cooldown aplicado, permitindo identificar contas sem nenhuma proxy saudável.
