# Matriz de rastreabilidade

| Solicitação original | Requisitos | Especificação principal | Marco de aceite |
|---|---|---|---|
| Dashboard e gráficos | RF-DAS-* | 12, 14, 15 | Marco 6 |
| Períodos do engajamento | RF-DAS-009 | 04, 07, 12, 16 | Hoje/Ontem/Mês/Personalizado respeitam timezone e snapshots cumulativos |
| Biblioteca/upload/preview/filtros | RF-MED-* | 10, 12 | Marco 3 |
| Dados de mídia | RF-MED-006 | 06, 10 | Marco 3 |
| Instagram Login sem Facebook Login | RF-ACC-001 | 08 | Marco 2 |
| Tela e ações de contas | RF-ACC-* | 07, 12 | Marco 2 |
| Remoção em massa | RF-ACC-016, RF-MED-012 e Proxy Manager | 07, 12, 13 | Até 200 itens, tenant isolado, confirmação e auditoria |
| Situação operacional ao vivo | RF-ACC-011 a RF-ACC-015 | 04, 06, 07, 08, 09, 12, 16 | Consulta oficial, histórico, WebSocket e bloqueio seguro de jobs |
| Criar campanhas visuais | RF-CAM-* | 04, 12 | Marco 4 |
| Feed/Reel/Story | RF-CAM-003 | 08 | Marcos 4–5 |
| Mesmo/sequencial/aleatório | RF-CAM-006/016/017 | 04, 06, 07, 09, 16, 19 ADR-011 | Distribuição independente por conta, seed reproduzível e execução em `plan_position` |
| Posts por hora/duração | RF-CAM-007 | 04, 18 DEC-003 | Marco 4 |
| Agendamento/timezone | RF-CAM-008 | 04, 09 | Marco 4 |
| Capa automática/customizada | RF-CAM-009 | 04, 08, 10 | Marco 4 |
| Worker independente | RF-SCH-004 | 05, 09 | Marco 5 |
| Scheduler por minuto | RF-SCH-001 | 09 | Marco 5 |
| Retentativa/backoff | RF-SCH-006 | 04, 09 | Marco 5 |
| Renovação de tokens | RF-SCH-008 | 08, 09 | Marcos 2 e 5 |
| Logs por publicação | RF-LOG-* | 07, 15 | Marco 5 |
| Admin e permissões | RF-ADM-* | 11, 13 | Marcos 1 e 7 |
| Usuário pendente/aprovação | RF-AUT-001/002/004 | 11 | Marco 1 |
| JWT/refresh/Supabase Auth | RF-AUT-003 | 11, 18 DEC-002 | Marco 1 |
| App por usuário cifrado | RF-SET-* | 08, 13 | Marco 1 |
| Tabelas solicitadas | RFs transversais | 06 | Marcos 0–7 |
| Endpoints modulares/OpenAPI | RF-API-* | 07 | Marcos 0–7 |
| Segurança e auditoria | RF-AUT/LOG/SET | 13 | Marco 7 |
| Backend assíncrono | Princípio | 02, 05, 14 | Marco 0 |
| UI premium/responsiva | RFs de UI | 12 | Todos os marcos com UI |
| Código modular/tipado | Qualidade | 05, 16 | Quality gate |
| Rascunho/duplicar | RF-CAM-001/012 | 04, 12 | Marco 4 |
| Tags | RF-MED-009 | 10 | Marco 3 |
| WebSocket | RF-DAS-007 | 07, 12, 15 | Marco 6 |
| Notificações | RF-NOT-* | 12, 15 | Marco 6 |
| Fuso por usuário | RF-SET-005 | 04, 11 | Marco 1 |
| Painel de saúde | RF-ADM-005 | 15 | Marco 7 |

## Cobertura

Todos os blocos da ideia original estão representados em ao menos um requisito, documento técnico e marco. Decisões ambíguas foram explicitadas em vez de assumidas silenciosamente.
# Proxy Manager

| Solicitação | Implementação | Aceite |
|---|---|---|
| Proxies próprios por usuário | `proxies`, RLS e API | Tenant não acessa registro alheio |
| Proxy configurada por campanha | campos da campanha, `campaign_proxies` e worker | Configuração aparece somente na campanha e aplica a mesma proxy à rodada |
| Teste e saúde | `ProxyManager`, tarefa e scheduler | IP/latência/status atualizados |
| Importação textual em massa | `POST /proxies/import` e tela Proxies | Formato `host:porta:usuário:senha`, erros por linha e nenhuma credencial no retorno |
| Rotação por campanha | `campaign_proxies`, `campaign_proxy_assignments`, `rotation_slot` e worker | Mesma proxy em todas as contas da rodada; troca por rodada ou X rodadas |
| Remoção em massa de proxies | `POST /proxies/bulk-remove`, `removed_at` e auditoria | Até 200 por lote; campanhas ativas bloqueiam a remoção |
| Fallback de proxy | cooldown em `proxies`, histórico no job/tentativa | Falha de transporte tenta outra proxy saudável sem conexão direta silenciosa |

# Ranking mensal

| Solicitação | Implementação | Aceite |
|---|---|---|
| Um ranking mensal geral | `/ranking/monthly`, índices de jobs/insights e `/app/ranking` | Mês completo, score único e métricas detalhadas por usuário ativo |
| Views com maior peso natural | soma bruta no serviço de ranking | Ordem reflete os valores reais sem normalização |
| Ver métricas de cada pessoa | cards por participante | Posts, views, curtidas, comentários, compartilhamentos, salvamentos e engajamento visíveis |
| Botão na base da sidebar | `AppShell` | Substitui o cartão promocional e funciona em desktop/mobile |
