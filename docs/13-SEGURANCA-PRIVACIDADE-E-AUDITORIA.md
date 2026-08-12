# Segurança, privacidade e auditoria

## 1. Modelo de ameaças resumido

Ativos críticos:

- App Secrets dos usuários;
- tokens do Instagram;
- exports de cookies processados localmente pela extensão opcional;
- sessão do usuário/admin;
- mídias privadas;
- capacidade de publicar;
- dados de analytics e auditoria.

Ameaças principais:

- acesso cruzado entre tenants;
- publicação não autorizada ou duplicada;
- furto de token/segredo;
- OAuth CSRF/replay;
- upload malicioso;
- abuso de endpoints em lote;
- SSRF por URLs;
- XSS/CSRF;
- privilégio administrativo indevido;
- vazamento por logs.

## 2. Criptografia

- TLS em trânsito.
- Segredos cifrados na aplicação antes do banco.
- Envelope encryption com chave mestra fora do banco e versionamento para rotação.
- AAD contendo tenant e finalidade para impedir troca de ciphertext.
- Hash não reversível para refresh tokens próprios, se existirem.
- Nunca usar criptografia caseira.

## 3. Isolamento

- `owner_id` obrigatório.
- autorização em service/policy.
- RLS como segunda barreira.
- caminhos de storage segregados.
- cache keys e filas namespaced por ambiente/tenant.
- nenhuma URL ou ID externo autoriza acesso por si só.
- testes automáticos de acesso horizontal.

## 4. OAuth

- state aleatório, curto, expirável e single-use;
- PKCE quando suportado;
- Redirect URI allowlisted;
- callback HTTPS;
- nenhuma credencial em query da UI;
- proteção contra account linking indevido;
- logs sanitizados;
- rate limit para início/callback.

## 5. JWT/sessão

- validar algoritmo esperado, assinatura, issuer, audience, `exp`, `nbf` quando usado e subject;
- não aceitar algoritmo vindo livremente do token;
- rotação de chaves;
- revogação por status/sessão;
- refresh rotation e reuse detection se tokens próprios;
- cookie seguro e CSRF quando autenticação por cookie.

## 6. CSRF, CORS e headers

- CORS allowlist explícita por ambiente; nunca `*` com credentials.
- CSRF token para mutações autenticadas por cookie.
- SameSite compatível com o fluxo real.
- CSP restritiva e sem `unsafe-eval` em produção.
- HSTS, `nosniff`, frame-ancestors e referrer policy.

## 7. Rate limit e abuso

Limites por IP, usuário, tenant, ação e dependência. Proteção reforçada para:

- login/cadastro;
- OAuth;
- upload session;
- ativação/duplicação em lote;
- retry manual;
- admin;
- WebSocket.

Respostas 429 não revelam existência de recursos de outro tenant.

## 8. Upload e mídia

- allowlist;
- limite de tamanho;
- inspeção de assinatura real;
- nomes não confiáveis;
- object keys geradas;
- scanning de malware como requisito de produção a decidir;
- processamento isolado com limites de CPU/memória/tempo;
- sem buscar URL arbitrária fornecida pelo usuário no MVP.

## 9. Logs

Proibido registrar:

- Authorization header;
- App Secret;
- access/refresh token;
- URL assinada completa;
- cookies;
- senha;
- payload bruto não sanitizado da Meta.

Sanitização deve ocorrer antes do logger, não apenas na interface.
Loggers de transporte HTTP (`httpx`/`httpcore`) permanecem em `WARNING` também nos processos Celery, pois URLs de integrações podem carregar credenciais na query string.

Exports de cookies nunca atravessam `fetch`, API, Supabase, Redis ou WebSocket. A extensão aceita apenas o domínio `instagram.com`, guarda a fila em `chrome.storage.session` restrito a contextos confiáveis, mascara o identificador exibido e remove os dados temporários quando solicitado ou quando a sessão do navegador termina. Arquivos reais não podem ser incluídos em fixtures, screenshots ou pacotes de distribuição.

No Story local, o backend entrega apenas o original por URL assinada de cinco minutos e nunca recebe `sessionid`, `csrftoken`, `ds_user_id` ou headers web. A extensão fixa as origens permitidas ao Instagram e ao host do projeto Supabase, confirma o `ds_user_id`, limita mídia, sanitiza erros e não persiste resposta bruta. O preset guarda somente `media_id`, link e título; a auditoria registra apenas IDs e hostname do destino. O recurso possui kill switch de ambiente.

## 10. Auditoria

Eventos mínimos:

- cadastro/aprovação/rejeição/suspensão;
- login/logout/revogação relevante;
- alteração de papel/permissão;
- configuração/rotação/remoção de Instagram App;
- conexão/reconexão/remoção de conta;
- ativação/pausa/cancelamento/duplicação de campanha;
- retry/cancelamento manual de job;
- exclusão de usuário/mídia;
- acesso administrativo sensível.

Registro: ator, ação, alvo, tenant, momento, request ID, IP reduzido conforme política, resultado e before/after sanitizado.

## 11. Privacidade e LGPD

Antes da produção:

- definir controlador/operador e bases legais;
- política de privacidade e termos;
- inventário e finalidade dos dados;
- retenção;
- exportação/correção/exclusão;
- subprocessadores;
- resposta a incidente;
- transferência internacional;
- contato de privacidade.

Isto é especificação técnica, não aconselhamento jurídico.

## 12. Administração e produção

- MFA obrigatório recomendado para admins.
- menor privilégio em Supabase/infra.
- ambientes separados.
- dados reais proibidos em desenvolvimento/teste.
- secrets manager.
- backups criptografados e teste de restauração.
- dependências com scanning e atualização.
- revisão de App Meta e políticas antes do go-live.

## 13. Critérios bloqueadores de produção

- threat model revisado;
- teste de tenant isolation;
- tokens/segredos não aparecem em logs;
- rotação de chave testada;
- restauração de backup testada;
- CSRF/CORS/CSP validados;
- fluxo de exclusão definido;
- rate limits ativos;
- resposta a incidente documentada.
# Credenciais de proxy

A senha é cifrada com AES-GCM e contexto por usuário/proxy, seguindo o mesmo cofre dos tokens. Logs e respostas removem senha/ciphertext; RLS restringe proxies ao proprietário e impede associação de proxy de outro tenant.

Logs de rotação registram somente identificador, nome, status e motivo da seleção/falha; nunca host autenticado, senha ou URL completa da proxy.
