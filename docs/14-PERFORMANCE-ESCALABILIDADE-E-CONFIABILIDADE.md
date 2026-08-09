# Performance, escalabilidade e confiabilidade

## 1. Objetivo

Preparar o desenho para milhares de contas conectadas sem prometer capacidade não medida. Escala é validada por teste e telemetria.

## 2. Metas iniciais propostas

| Indicador | Meta |
|---|---|
| API leitura simples p95 | < 300 ms, excluindo dependências externas |
| API comando p95 | < 500 ms até persistir/enfileirar |
| Disponibilidade API mensal | 99,9% após produção estável |
| Início de job p99 | até 60 s do horário, salvo throttling externo |
| Dashboard inicial p75 | LCP < 2,5 s em condição definida |
| Duplicação interna de publicação | 0 |

As condições e volumes do teste deverão acompanhar cada número.

## 3. Banco

- SQLAlchemy assíncrono com driver compatível.
- Pool por processo dimensionado ao limite total, não por instância isolada.
- Supabase pooler quando apropriado.
- queries paginadas e índices guiados por planos reais.
- agregados de dashboard pré-calculados quando necessário.
- evitar N+1.
- transações curtas.
- tabelas de logs/attempts particionáveis por tempo se volume justificar.

## 4. API

- stateless;
- I/O assíncrono;
- nenhuma conversão de mídia;
- limites de payload;
- compressão quando útil;
- cache apenas para leituras seguras;
- timeouts e pool de conexão httpx;
- circuit breaker/bulkhead no cliente externo, implementados com cuidado.

## 5. Filas

- payload pequeno com ID.
- backlog, idade do job e taxa de retry monitorados.
- workers escalados por fila.
- prefetch/concurrency ajustados ao rate limit, não apenas à CPU.
- filas separadas para publicação, mídia, insights e manutenção.
- Redis indisponível não perde intenção persistida.

## 6. Cache

Candidatos:

- permissões/status com TTL curto e invalidação;
- resumo do dashboard;
- configuração não secreta;
- limites externos;
- presença WebSocket.

Não cachear ciphertext/tokens fora do necessário. Cache miss nunca ignora tenant scope.

## 7. Dashboard

- endpoints agregados em vez de dezenas de chamadas;
- janelas de tempo pré-agregadas;
- timezone calculado de forma consistente;
- WebSocket envia deltas;
- séries limitadas e downsampled.

## 8. Resiliência externa

- timeout por fase;
- retries somente idempotentes/classificados;
- jitter;
- `Retry-After`;
- circuit breaker por App/endpoint para evitar efeito cascata;
- degradação: UI continua acessível mesmo se a Meta estiver indisponível;
- status do provider separado do status interno.

## 9. Capacity planning

Variáveis:

- tenants;
- contas por tenant;
- campanhas simultâneas;
- jobs por minuto;
- tamanho médio de mídia;
- chamadas Meta por publicação;
- frequência de insights;
- retenção de logs.

Antes de produção, criar cenários mínimo, esperado e pico, calculando conexões, throughput de fila, requests externos, storage e crescimento de banco.

## 10. Testes de carga

No mínimo:

- leitura de dashboard;
- filtros de mídia;
- ativação concorrente de campanhas;
- materialização de grande volume de jobs;
- dispatcher;
- workers com API Meta simulada;
- tempestade de 429/5xx;
- queda/reinício de Redis;
- queda de worker no meio da publicação;
- WebSockets concorrentes.

Testes contra a Meta real respeitarão políticas e limites; carga pesada usa simulador.

## 11. Backups e disaster recovery

Definir e testar:

- RPO e RTO;
- backup e point-in-time recovery do PostgreSQL;
- estratégia para objetos no Storage;
- restore em ambiente isolado;
- reconstrução de Redis;
- reconciliação de jobs após restore;
- proteção contra republicar jobs antigos.

## 12. Evolução

Extrair microserviços somente com evidência de gargalo, ownership ou isolamento. Candidatos futuros: mídia e publishing. O monólito modular permanece preferível no início.

