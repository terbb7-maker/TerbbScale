# Scheduler, workers e filas

## 1. Objetivo

Executar milhares de publicações planejadas sem bloquear a API, sem duplicação e com recuperação após falhas.

## 2. Separação de responsabilidades

| Componente | Faz | Não faz |
|---|---|---|
| API | valida e persiste comandos | publica mídia |
| Planner | transforma campanha em jobs | chama a Meta |
| Dispatcher | encontra jobs devidos e enfileira | muda regra da campanha |
| Publishing worker | executa uma publicação | recalcula toda campanha |
| Maintenance worker | tokens, insights, reconciliação | atende HTTP do usuário |
| Redis | transporte/coordenação efêmera | fonte de verdade |
| PostgreSQL | estado, locks duráveis, idempotência | transporte de payload pesado |

## 3. Ciclo do scheduler

A cada minuto:

1. adquirir lease do shard/janela;
2. buscar campanhas novas ou alteradas;
3. validar elegibilidade;
4. criar versão/snapshot quando necessário;
5. materializar jobs futuros dentro de um horizonte;
6. buscar jobs devidos ainda não enviados;
7. enfileirar somente o ID do job;
8. atualizar checkpoint e métricas;
9. liberar/expirar lease.

O intervalo de um minuto é discovery/planning. Jobs podem ser agendados em segundos exatos e entregues por mecanismo de fila/dispatcher.

## 4. Planejamento determinístico

Entradas:

- versão da campanha;
- contas ordenadas e capacidades;
- mídias ordenadas;
- estratégia;
- throughput;
- duração;
- início/timezone;
- limites conhecidos.

Saída: lista imutável de jobs com `account_id`, `media_id`, `scheduled_at`, `plan_position` e chave de idempotência. Rodar o mesmo plano com o mesmo seed deve produzir a mesma distribuição e as mesmas chaves.

## 5. Concorrência

- Lock de planejamento por campanha/versão.
- Reserva de job via update condicional ou `FOR UPDATE SKIP LOCKED`.
- Lease com expiração para recuperar worker morto.
- Um job só transita do estado esperado.
- Dentro da mesma conta e versão de campanha, apenas o primeiro job não finalizado pode publicar; um lock Redis por conta impede chamadas externas concorrentes e um predecessor pendente causa reagendamento sem consumir tentativa.
- Resultado externo confirmado bloqueia nova chamada de publicação.
- Contadores da campanha são derivados/reconciliáveis, não única fonte de verdade.

## 6. Retentativa

Política proposta:

```text
delay = min(base × 2^(attempt-1), maximum) + jitter
```

- respeitar `Retry-After`;
- limites diferentes por classe de erro;
- orçamento máximo de tentativas e tempo;
- retentativa nunca ultrapassa uma janela de validade sem revalidar mídia, token e campanha;
- falha permanente vai diretamente ao estado final;
- esgotamento vai para dead-letter e notificação.

Valores iniciais serão configuráveis por ambiente e aprovados em runbook.

## 7. Rate limiter distribuído

Chaves independentes por:

- tenant/App;
- conta do Instagram;
- operação/endpoint;
- limite global de proteção.

Algoritmo sugerido: token bucket/sliding window em Redis com operação atômica. O limite oficial conhecido no banco atua junto ao limiter efêmero.

## 8. Priorização e fairness

- Jobs vencidos primeiro, sem fome para tenants menores.
- Fair scheduling por tenant/conta.
- Manutenção não deve consumir toda a capacidade de publicação.
- Retry não deve criar tempestade.
- Prioridade administrativa excepcional deve ser auditada.

## 9. Renovação de token

Worker periódico:

1. busca tokens dentro da janela de renovação;
2. adquire lock por token;
3. verifica suporte e estado;
4. renova;
5. persiste ciphertext e nova expiração atomicamente;
6. atualiza conta;
7. emite notificação em falha.

Nenhum token é enviado como payload de fila.

## 10. Coleta de insights

Cadência proposta:

- uma coleta imediata ao iniciar o scheduler e depois de uma reconexão OAuth;
- descoberta de novas publicações a cada 5 minutos;
- publicações de até 48 horas: recaptura mínima a cada 5 minutos;
- publicações de até 7 dias: recaptura mínima a cada 30 minutos;
- publicações antigas, até 30 dias: recaptura mínima a cada 6 horas;
- campanha finalizada: consolidar e reduzir polling.

Jobs de insights são separados da fila de publicação e respeitam rate limit próprio.
Falhas de permissão são registradas, notificadas ao usuário e não alteram uma conta com token válido para `expired`.

## 10. Monitor de situação das contas

O scheduler procura, a cada minuto, até 500 contas vencidas em `health_next_check_at`, faz claim com `FOR UPDATE SKIP LOCKED` e envia verificações à fila de manutenção. Cada worker consulta a API oficial de forma independente da API principal, aplica classificação tipada, atualiza o resumo, registra somente transições/verificações manuais relevantes, notifica o usuário e publica `account.health_updated` no canal Redis/WebSocket. Contas saudáveis são verificadas novamente em poucos minutos; falhas possuem backoff conforme a classe.

## 11. Celery versus alternativa

### Opção proposta

Usar Celery com Redis se, no momento da implementação, houver compatibilidade confirmada com Python 3.13 e os requisitos de agendamento/ack. APScheduler permanece no planner.

### Alternativa

Worker AsyncIO próprio consumindo Redis Streams e estado no PostgreSQL. Oferece controle assíncrono, mas aumenta responsabilidade operacional.

A escolha é bloqueadora e está em `18-DECISOES-PENDENTES.md`.

## 12. Desligamento e recuperação

- Worker para de reservar novos jobs.
- Conclui ou devolve leases dentro do grace period.
- Jobs abandonados são recuperados após lease.
- Deploy não pode causar publicação dupla.
- Redis vazio pode ser reconstruído a partir de jobs pendentes no PostgreSQL.

## 13. SLOs operacionais propostos

- 99% dos jobs elegíveis iniciam até 60 segundos após `scheduled_at`, exceto throttling externo.
- Nenhuma duplicação atribuível a retentativa interna.
- Job órfão detectado em até 5 minutos.
- Campanha reconciliada em até 10 minutos após evento de falha interna.
# Saúde de proxies

O scheduler enfileira uma verificação de proxies ativos a cada cinco minutos na fila de manutenção. O worker mede resposta/IP com concorrência limitada e não bloqueia a API principal. Um teste manual reflete a falha imediatamente; o monitor periódico exige três falhas consecutivas antes de retirar uma proxy previamente saudável da rotação. Um sucesso zera o contador.

Os containers Python usam resolvers DNS públicos definidos explicitamente na infraestrutura. Falhas de resolução, timeout, conexão, autenticação e resposta HTTP são classificadas sem expor host com credenciais ou mensagens internas.

Falha de transporte durante uma publicação marca a proxy em cooldown; a próxima tentativa escolhe outra proxy saudável do pool quando existir. A seleção e o contador são persistidos antes do post.
