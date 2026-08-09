# Plano de entrega e aceite

Este plano não autoriza execução. Ele define uma sequência possível após aprovação explícita.

## Marco 0 — Fundação e risco técnico

### Entregas

- estrutura modular;
- ambientes/configuração;
- conexão assíncrona com Supabase PostgreSQL/Redis;
- observabilidade base;
- modelo de erro;
- spike autorizado da Instagram API com Instagram Login;
- decisão de sessão e fila.

### Aceite

- API health/readiness;
- nenhum segredo versionado;
- conexão oficial comprovada em conta de teste;
- compatibilidade Python 3.13 validada;
- decisões críticas registradas.

## Marco 1 — Identidade, aprovação e configurações

### Entregas

- Supabase Auth;
- perfil `pending`;
- admin aprova/suspende;
- RBAC;
- timezone;
- Instagram App por usuário cifrado.

### Aceite

- pendente não acessa aplicação;
- aprovação libera;
- suspensão revoga;
- tenant não lê configuração alheia;
- segredo nunca retorna ou aparece em log.

## Marco 2 — Contas Instagram

### Entregas

- OAuth com Instagram Login;
- listagem/status;
- reconexão/remoção;
- token e expiração;
- health/renovação suportada.
- monitor assíncrono de situação operacional, histórico e atualização em tempo quase real.

### Aceite

- nenhuma dependência de Facebook Login;
- state de uso único;
- conta profissional conectada;
- token cifrado;
- falha/revogação refletida na UI.
- conta operacional confirmada por consulta oficial; ação/checkpoint e possível suspensão exibidos com confiança correta;
- conta bloqueada não recebe publicação até recuperação confirmada, e indisponibilidade da Meta não gera falso bloqueio definitivo.

## Marco 3 — Biblioteca de mídia

### Entregas

- upload múltiplo direto;
- processamento;
- thumbnail/metadados/hash;
- tags/busca/filtros;
- compatibilidade.

### Aceite

- upload grande não bloqueia API;
- tenant isolation;
- falha parcial clara;
- mídia inválida não fica `ready`;
- exclusão respeita referências.
- thumbnails privadas aparecem no grid e a remoção em massa respeita o tenant e a retenção.

## Marco 4 — Campanhas e planejamento

### Entregas

- rascunho;
- seleção de contas/mídias;
- três estratégias;
- frequência/duração/timezone;
- capa;
- preview/validação;
- versionamento/duplicação.

### Aceite

- preview determinístico;
- sequencial avança individualmente em cada conta;
- aleatório não repete na mesma conta antes de esgotar;
- preview e ativação materializam o mesmo plano/seed;
- jobs da mesma conta respeitam a posição planejada mesmo quando ficam devidos juntos;
- DST tratado;
- campanha inválida não ativa;
- snapshot não muda retroativamente.

## Marco 5 — Publicação oficial

### Entregas

- scheduler;
- Redis/fila;
- publishing worker;
- container/publish;
- idempotência;
- retries/dead-letter;
- logs.

### Aceite

- rota retorna sem aguardar publicação;
- worker independente;
- queda/retry não duplica;
- 429 respeitado;
- resultado rastreável;
- publicação Feed/Reel/Story somente conforme suporte validado.

## Marco 6 — Dashboard, insights e realtime

### Entregas

- KPIs;
- gráficos;
- insights;
- próximas/campanhas ativas/logs/erros;
- WebSocket;
- notificações.

### Aceite

- períodos/timezone corretos;
- filtros Hoje, Ontem, Mês e Personalizado alteram todas as métricas de engajamento de forma consistente;
- métrica indisponível não vira zero;
- atualização sem refresh;
- fallback após desconexão;
- queries dentro do budget.

## Marco 7 — Operação, admin e produção

### Entregas

- planos/limites sem cobrança ou com provedor aprovado;
- painel de saúde;
- alertas/runbooks;
- segurança;
- carga;
- backup/restore;
- deploy.

### Aceite

- quality gates;
- testes de isolamento/idempotência;
- restore testado;
- SLOs medidos;
- App Review/permissões prontos;
- checklist de produção aprovado.

## Critérios de aceite do produto

1. Todo tráfego de Instagram usa API oficial com Instagram Login.
2. Um tenant nunca acessa credenciais ou recursos de outro.
3. Publicação não bloqueia API.
4. Worker e scheduler recuperam falhas sem duplicação interna.
5. Campanha possui plano auditável.
6. Tokens/segredos ficam cifrados e fora de logs.
7. UI é utilizável em desktop e mobile.
8. Métricas são semanticamente corretas e marcam indisponibilidade.
9. Administrador controla aprovação com auditoria.
10. Saúde, backlog e falhas são observáveis.
11. A identidade pública é Terbb Scale e a navegação principal é compreensível sem treinamento.
12. Contas, mídias e proxies possuem seleção e remoção em massa com confirmação.

## Estratégia de release

- desenvolvimento local;
- integração automatizada;
- staging com Supabase/Redis isolados;
- contas Meta de teste;
- produção com feature flags e rollout gradual;
- publicação real inicialmente limitada a allowlist;
- rollback e kill switch por App/tenant/campanha.
# Marco — Proxy Manager

Aceite: CRUD seguro, teste de IP/latência, pool e rotação por conta, seleção na campanha, uso pelo worker/insights/renovação, health check periódico, cooldown/fallback de transporte, dashboard e interfaces responsivas, com testes e deploy validados.

# Marco — Ranking mensal

Aceite: o cartão inferior da sidebar abre `/app/ranking`; existe um único score geral com peso natural das métricas; o período cobre o mês-calendário completo de Brasília; cada participante mostra posts, views, curtidas, comentários, compartilhamentos, salvamentos e engajamento; a posição do usuário atual é destacada; e-mails e dados privados não são expostos; desktop e mobile são validados.
