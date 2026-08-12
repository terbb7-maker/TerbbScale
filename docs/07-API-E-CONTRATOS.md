# API e contratos

## 1. Convenções

- Prefixo proposto: `/api/v1`.
- JSON em `snake_case`.
- Datas em ISO 8601 com offset; persistência UTC.
- IDs opacos UUID.
- Paginação por cursor para listas mutáveis.
- `Idempotency-Key` obrigatório em criação/ativação de campanha, publicação imediata e mutações externas críticas.
- `X-Request-ID` aceito ou gerado.
- OpenAPI gerada pelo FastAPI.

## 2. Envelope de erro

```json
{
  "error": {
    "code": "campaign_not_ready",
    "message": "A campanha possui bloqueios.",
    "details": [],
    "request_id": "opaque-id"
  }
}
```

Mensagens públicas não contêm stack trace, segredo, token, SQL ou resposta sensível da Meta.

## 3. Semântica HTTP

- `200`: leitura/alteração síncrona concluída.
- `201`: recurso criado.
- `202`: comando aceito para processamento assíncrono.
- `204`: operação concluída sem corpo.
- `400`: comando inválido.
- `401`: identidade ausente/inválida.
- `403`: sem permissão, pendente ou suspenso.
- `404`: inexistente ou invisível ao tenant.
- `409`: conflito de estado/idempotência.
- `422`: validação estrutural.
- `429`: rate limit.
- `503`: dependência indisponível.

## 4. Endpoints propostos

### `/auth`

| Método | Rota | Resultado |
|---|---|---|
| POST | `/auth/register` | Cria perfil pendente vinculado ao Supabase Auth |
| POST | `/auth/session/exchange` | Estabelece contexto da aplicação, se necessário |
| POST | `/auth/refresh` | Renova sessão conforme modelo aprovado |
| POST | `/auth/logout` | Revoga sessão atual |
| GET | `/auth/me` | Perfil, status, papéis e permissões |

### `/settings`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/settings` | Configurações mascaradas |
| PUT | `/settings/profile` | Timezone e preferências |
| PUT | `/settings/instagram-app` | Salva credenciais cifradas |
| POST | `/settings/instagram-app/validate` | Validação assíncrona/sanitizada |
| DELETE | `/settings/instagram-app` | Remove credenciais após checar impactos |

### `/accounts`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/accounts` | Lista paginada e filtrável |
| POST | `/accounts/connect` | Gera URL OAuth + state |
| GET | `/accounts/oauth/callback` | Consome callback e redireciona para UI |
| POST | `/accounts/{id}/reconnect` | Inicia novo OAuth |
| POST | `/accounts/{id}/refresh-token` | Solicita renovação suportada |
| POST | `/accounts/{id}/health-check` | Agenda verificação |
| GET | `/accounts/{id}/health-checks` | Lista histórico recente da situação operacional |
| DELETE | `/accounts/{id}` | Remove conexão com confirmação |
| POST | `/accounts/bulk-remove` | Remove até 200 contas do tenant, revoga tokens e cancela jobs futuros |

### `/cookie-story`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/cookie-story/preset` | Lê o preset do tenant com preview temporário |
| PUT | `/cookie-story/preset` | Cria ou substitui mídia/link do preset |
| DELETE | `/cookie-story/preset` | Remove o preset |
| POST | `/cookie-story/delivery` | Valida novamente e assina o original por cinco minutos para a extensão |

`/delivery` nunca recebe cookie ou identificador do Instagram e nunca executa a publicação. A resposta sensível não pode ser registrada e expira rapidamente.

### `/media`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/media` | Lista, pesquisa e filtros |
| POST | `/media/uploads` | Cria sessão de upload |
| POST | `/media/uploads/{id}/complete` | Confirma upload e agenda processamento |
| GET | `/media/{id}` | Detalhe e compatibilidade |
| PATCH | `/media/{id}` | Nome/tags/metadados editáveis |
| DELETE | `/media/{id}` | Arquiva ou agenda exclusão |
| POST | `/media/previews` | Assina previews privados de até 200 mídias em lote |
| POST | `/media/bulk-remove` | Agenda exclusão segura de até 200 mídias |
| POST | `/media/bulk/tags` | Tags em lote |

### `/campaigns`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/campaigns` | Lista e filtros |
| POST | `/campaigns` | Cria rascunho |
| GET | `/campaigns/{id}` | Definição, estado e progresso |
| PATCH | `/campaigns/{id}` | Edita estado compatível |
| POST | `/campaigns/{id}/validate` | Retorna bloqueios e avisos |
| POST | `/campaigns/{id}/preview` | Plano determinístico sem ativar |
| POST | `/campaigns/{id}/activate` | Versiona, planeja e agenda |
| POST | `/campaigns/{id}/duplicate` | Novo rascunho |
| POST | `/campaigns/{id}/pause` | Pausa futuros jobs |
| POST | `/campaigns/{id}/resume` | Retoma |
| POST | `/campaigns/{id}/cancel` | Cancela |
| GET | `/campaigns/{id}/jobs` | Publicações planejadas |

O preview retorna `planning_seed` e uma amostra dos itens com conta, mídia, horário e posição. A ativação reutiliza esse seed somente quando o payload não mudou, garantindo que o plano validado seja o plano materializado. O detalhe dos jobs inclui `plan_position` e `rotation_slot` para auditoria da ordem.

### `/dashboard`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/dashboard/summary` | KPIs e engajamento; aceita `period=today|yesterday|month|custom` e, em `custom`, `date_from`/`date_to` inclusivos |
| GET | `/dashboard/timeseries` | Séries temporais |
| GET | `/dashboard/upcoming` | Próximas publicações |
| GET | `/dashboard/running` | Campanhas em execução |
| WS | `/dashboard/events` | Eventos autorizados do tenant |

### `/logs`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/logs/publications` | Logs filtráveis |
| GET | `/logs/publications/{id}` | Detalhe sanitizado |
| GET | `/logs/audit` | Somente permissões elevadas |

### `/scheduler`

Rotas de usuário devem ser majoritariamente read-only. Comandos operacionais ficam restritos:

| Método | Rota | Resultado |
|---|---|---|
| GET | `/scheduler/status` | Estado e atraso |
| GET | `/scheduler/jobs` | Jobs autorizados |
| POST | `/scheduler/jobs/{id}/retry` | Retry manual com auditoria |
| POST | `/scheduler/jobs/{id}/cancel` | Cancelamento autorizado |

### `/admin`

| Método | Rota | Resultado |
|---|---|---|
| GET | `/admin/users` | Lista usuários |
| POST | `/admin/users/{id}/approve` | Aprova |
| POST | `/admin/users/{id}/reject` | Rejeita |
| POST | `/admin/users/{id}/suspend` | Suspende e revoga |
| POST | `/admin/users/{id}/reactivate` | Reativa |
| DELETE | `/admin/users/{id}` | Inicia exclusão |
| GET/POST/PATCH | `/admin/plans...` | Gerencia planos |
| GET | `/admin/stats` | Estatísticas globais |
| GET | `/admin/health` | Saúde sanitizada |

## 5. Operações em lote

- Máximo por requisição definido por plano e proteção operacional.
- Resultado parcial retorna item a item; não mascara falhas.
- Toda ação em lote gera um operation ID para acompanhamento.
- “Selecionar todas” no frontend deve representar o filtro atual, não enviar milhares de IDs sem necessidade.

## 6. Concorrência

Mutações de campanha usam versão/ETag. Atualização com versão antiga retorna `409`. Ativar campanha é transacional e idempotente.

## 7. WebSocket

- Autenticação no handshake ou primeiro frame, sem token em query string persistida em logs.
- Canais isolados por tenant.
- Eventos contêm IDs e resumo; dados completos são buscados por REST.
- Cliente reconecta com backoff e recupera lacunas usando cursor de evento.

## 8. Contratos externos

O adapter do Instagram expõe operações tipadas:

- construir URL de autorização;
- trocar código por token;
- renovar token quando suportado;
- obter perfil/conta;
- criar container;
- consultar status do container;
- publicar container;
- consultar limite de publicação;
- buscar insights suportados.

Versões e payloads concretos serão fixados após revalidação da documentação oficial.
# Proxy Manager

- `GET/POST /proxies`; `PUT/DELETE /proxies/{id}`
- `POST /proxies/bulk-remove`: remove logicamente até 200 proxies; rejeita o lote quando alguma estiver em campanha ativa.
- `POST /proxies/import`: recebe até 500 linhas em `entries`, cada uma no formato `host:porta:usuário:senha`; retorna contagem criada/rejeitada e erros somente por número da linha.
- `POST /proxies/{id}/test`; `POST /proxies/test-all`
- `POST/DELETE /accounts/{id}/proxy`; `POST /accounts/proxy/bulk`
- `GET/PUT /accounts/{id}/proxy-pool`: consulta ou substitui o pool ordenado e a política `fixed`, `per_post` ou `every_n_posts` da conta.

Todos exigem sessão ativa e isolam registros por `owner_id`. A resposta nunca contém senha ou ciphertext.

# Ranking

- `GET /ranking/monthly?month=AAAA-MM`: retorna período completo, estado do mês, total de participantes e classificação geral.
- Cada entrada contém posição, nome, avatar opcional, marcador do usuário atual, score, posts, views, curtidas, comentários, compartilhamentos, salvamentos e engajamento.
- Mês futuro é rejeitado com `future_ranking_month`; acesso exige usuário ativo.
- O contrato nunca retorna e-mail ou credenciais de outro usuário.
