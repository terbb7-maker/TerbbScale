# Requisitos funcionais

Os identificadores `RF-*` são estáveis e usados na matriz de rastreabilidade.

## RF-AUT — Autenticação e acesso

- **RF-AUT-001:** permitir criação de usuário com estado inicial `pending`.
- **RF-AUT-002:** impedir acesso às áreas protegidas enquanto o usuário não estiver `active`.
- **RF-AUT-003:** permitir login, logout e renovação segura de sessão.
- **RF-AUT-004:** permitir que administrador aprove, rejeite, suspenda ou reative um usuário.
- **RF-AUT-005:** aplicar permissões customizadas por papel e, quando necessário, por usuário.
- **RF-AUT-006:** revogar sessões ativas quando um usuário for suspenso ou excluído.
- **RF-AUT-007:** permitir recuperação de senha pelo mecanismo aprovado do Supabase Auth.

## RF-SET — Configurações

- **RF-SET-001:** cada usuário poderá cadastrar seu próprio Instagram App ID, App Secret, Redirect URI e scopes.
- **RF-SET-002:** App Secret deverá ser criptografado antes de persistir.
- **RF-SET-003:** a API nunca retornará o App Secret completo após salvá-lo.
- **RF-SET-004:** validar a configuração sem revelar segredo em logs ou mensagens.
- **RF-SET-005:** permitir definir timezone padrão do usuário.
- **RF-SET-006:** impedir qualquer uso cruzado das credenciais de outro usuário.

## RF-ACC — Contas do Instagram

- **RF-ACC-001:** conectar conta por Instagram Login, sem Facebook Login.
- **RF-ACC-002:** persistir identificador externo, nome, username, foto quando disponível, token cifrado, expiração, scopes e status.
- **RF-ACC-003:** exibir posts publicados e data da última publicação.
- **RF-ACC-004:** permitir reconectar uma conta.
- **RF-ACC-005:** permitir solicitar atualização/renovação de token quando suportado.
- **RF-ACC-006:** permitir remover uma conta após confirmação.
- **RF-ACC-007:** permitir seleção individual, múltipla e “selecionar todas”.
- **RF-ACC-008:** identificar contas conectadas, expiradas, revogadas, com erro e removidas.
- **RF-ACC-009:** impedir duplicidade da mesma conta externa dentro do mesmo tenant.
- **RF-ACC-010:** verificar estado da conexão sem bloquear a requisição principal.
- **RF-ACC-011:** monitorar em background a situação operacional de cada conta usando somente respostas da API oficial.
- **RF-ACC-012:** distinguir conta operacional, reconexão necessária, ação/checkpoint solicitado, permissão ausente, restrição temporária, possível suspensão inferida e indisponibilidade da Meta.
- **RF-ACC-013:** informar o nível de confiança da situação (`confirmed`, `inferred` ou `unknown`) e nunca apresentar inferência como confirmação da Meta.
- **RF-ACC-014:** disponibilizar verificação manual, histórico recente, códigos sanitizados e atualização em tempo quase real.
- **RF-ACC-015:** suspender e reagendar publicações de contas com ação necessária, sem consumir tentativas enquanto o bloqueio persistir.
- **RF-ACC-016:** permitir remover até 200 contas selecionadas em uma única ação, revogando tokens e cancelando jobs futuros das contas removidas.

## RF-MED — Biblioteca de mídias

- **RF-MED-001:** upload de imagens e vídeos.
- **RF-MED-002:** upload múltiplo com drag and drop.
- **RF-MED-003:** progresso individual por arquivo e tratamento de falha parcial.
- **RF-MED-004:** preview de imagem e vídeo.
- **RF-MED-005:** filtros por tipo, status e data, além de pesquisa textual.
- **RF-MED-006:** armazenar nome, tipo MIME, categoria, duração, peso, thumbnail, resolução, hash e data de upload.
- **RF-MED-007:** extrair metadados e gerar thumbnail em processo assíncrono.
- **RF-MED-008:** detectar conteúdo duplicado pelo hash dentro do tenant, com política configurável.
- **RF-MED-009:** permitir tags por mídia.
- **RF-MED-010:** permitir exclusão segura, bloqueando ou adiando a remoção quando houver uso ativo.
- **RF-MED-011:** informar compatibilidade da mídia com Feed, Reel e Story.
- **RF-MED-012:** permitir selecionar e remover até 200 mídias em lote, aplicando a mesma retenção segura da remoção individual.
- **RF-MED-013:** exibir a thumbnail processada no grid por URL privada assinada e temporária.

## RF-CAM — Campanhas

- **RF-CAM-001:** criar, editar e salvar campanha como rascunho.
- **RF-CAM-002:** definir nome, descrição interna, legenda, hashtags e tipo de publicação.
- **RF-CAM-003:** suportar Feed, Reel e Story quando permitidos pela API e conta.
- **RF-CAM-004:** selecionar uma, várias ou todas as contas elegíveis.
- **RF-CAM-005:** selecionar uma, várias ou todas as mídias elegíveis.
- **RF-CAM-006:** configurar estratégia `same_media`, `sequential` ou `random_without_replacement`.
- **RF-CAM-007:** configurar quantidade de posts por hora e duração em horas.
- **RF-CAM-008:** publicar agora ou agendar por data, hora e timezone.
- **RF-CAM-009:** permitir capa automática ou personalizada quando o formato/API aceitar.
- **RF-CAM-010:** validar a campanha antes da ativação e listar todos os bloqueios.
- **RF-CAM-011:** calcular e mostrar preview do plano de publicações.
- **RF-CAM-012:** duplicar campanha sem copiar estados de execução.
- **RF-CAM-013:** pausar, retomar ou cancelar campanha, respeitando jobs já em execução.
- **RF-CAM-014:** exibir progresso, publicações restantes, sucessos e falhas.
- **RF-CAM-015:** manter histórico imutável do plano efetivamente executado.
- **RF-CAM-016:** distribuir `sequential` e `random_without_replacement` de forma independente por conta, sem repetir uma mídia na mesma conta antes de esgotar o conjunto permitido.
- **RF-CAM-017:** persistir a posição do plano e impedir que publicações posteriores da mesma conta/versão ultrapassem predecessoras ainda não finalizadas.

## RF-SCH — Scheduler, fila e worker

- **RF-SCH-001:** scheduler independente verifica campanhas ao menos uma vez por minuto.
- **RF-SCH-002:** calcular horários e materializar jobs de publicação.
- **RF-SCH-003:** enfileirar jobs sem bloquear a API principal.
- **RF-SCH-004:** worker independente executa publicação e atualiza o banco.
- **RF-SCH-005:** usar idempotência para impedir publicação duplicada.
- **RF-SCH-006:** retentar falhas temporárias com backoff exponencial e jitter.
- **RF-SCH-007:** não retentar automaticamente falhas permanentes sem mudança de entrada.
- **RF-SCH-008:** renovar tokens antes do vencimento quando suportado.
- **RF-SCH-009:** respeitar limites por conta, app e plataforma.
- **RF-SCH-010:** recuperar jobs presos após queda de worker.
- **RF-SCH-011:** manter dead-letter state para falhas esgotadas.

## RF-LOG — Logs e auditoria

- **RF-LOG-001:** cada tentativa de publicação gera registro.
- **RF-LOG-002:** registrar conta, campanha, mídia, horário previsto, início, fim, latência, status e erro sanitizado.
- **RF-LOG-003:** guardar identificadores e resposta necessária da API com política de redação e retenção.
- **RF-LOG-004:** permitir filtros, paginação e exportação futura.
- **RF-LOG-005:** registrar ações administrativas e alterações críticas em audit log append-only.
- **RF-LOG-006:** correlacionar requisição, job, tentativa e chamada externa.

## RF-DAS — Dashboard e analytics

- **RF-DAS-001:** mostrar totais de contas, contas conectadas e expiradas.
- **RF-DAS-002:** mostrar campanhas ativas, finalizadas e em execução.
- **RF-DAS-003:** mostrar publicações hoje, ontem, 7 dias e 30 dias.
- **RF-DAS-004:** mostrar views, curtidas, comentários, compartilhamentos, salvamentos e engajamento médio quando disponíveis.
- **RF-DAS-005:** mostrar próximas publicações, logs recentes e erros recentes.
- **RF-DAS-006:** gráficos de publicações por dia, views por dia, crescimento e uso de contas.
- **RF-DAS-007:** atualizar eventos operacionais em tempo quase real via WebSocket ou fallback.
- **RF-DAS-008:** informar dado indisponível em vez de apresentar zero incorreto.
- **RF-DAS-009:** permitir classificar views, curtidas, comentários, compartilhamentos, salvamentos e taxa de engajamento por Hoje, Ontem, mês-calendário atual e período personalizado.

## RF-NOT — Notificações

- **RF-NOT-001:** toast para feedback imediato de ações.
- **RF-NOT-002:** central persistente de notificações.
- **RF-NOT-003:** notificar conclusão, falha relevante, token próximo de expirar e problema de conta.
- **RF-NOT-004:** marcar como lida individualmente ou em lote.

## RF-ADM — Administração

- **RF-ADM-001:** área administrativa protegida por permissão.
- **RF-ADM-002:** listar e filtrar usuários, aprovações, planos, logs e estatísticas.
- **RF-ADM-003:** aprovar, suspender, editar e excluir usuário com confirmação e auditoria.
- **RF-ADM-004:** gerenciar definições de planos e limites, após aprovação do modelo comercial.
- **RF-ADM-005:** visualizar saúde de banco, API, workers, filas, Redis e storage.
- **RF-ADM-006:** administradores não podem ver segredos ou tokens em texto aberto.

## RF-API — API

- **RF-API-001:** expor módulos `/auth`, `/accounts`, `/media`, `/campaigns`, `/dashboard`, `/admin`, `/settings`, `/logs` e `/scheduler`.
- **RF-API-002:** fornecer OpenAPI automaticamente.
- **RF-API-003:** aplicar paginação, filtros, validação e erros padronizados.
- **RF-API-004:** aceitar chave de idempotência nas mutações críticas.
- **RF-API-005:** versionar a API pública.
# Módulo Proxy Manager — requisito aprovado em 31 de julho de 2026

O sistema permite ao usuário cadastrar proxies HTTP, HTTPS e SOCKS5 próprios; testar IP público e latência; e configurar, em cada campanha, conexão direta, proxy fixa ou rotação do pool global por post/a cada X posts. Senhas nunca são retornadas pela API.

O cadastro também aceita importação em massa, com uma entrada por linha no formato `host:porta:usuário:senha` (inclusive quando houver apenas uma linha). Linhas inválidas não impedem a importação das demais e recebem retorno pelo número da linha, sem repetir credenciais.

Uma campanha pode usar o pool global do usuário e escolher proxy fixa, troca a cada rodada de posts ou troca a cada X rodadas. Uma rodada usa a mesma proxy em todas as contas e a mantém durante todas as etapas de cada publicação. A biblioteca de proxies permite remoção individual e de até 200 itens em lote; proxies usadas por campanhas ativas não podem ser removidas.

# Ranking mensal

Usuários ativos possuem acesso a um ranking geral mensal da comunidade. O período sempre começa no primeiro dia e termina no último dia do mês no horário de Brasília. Participam somente usuários com pelo menos uma publicação concluída com sucesso no período.

O ranking não possui categorias separadas. A posição usa um score único, calculado pela soma bruta de publicações, views, curtidas, comentários, compartilhamentos, salvamentos e taxa de engajamento. Views mantêm seu peso natural pelo volume. Cada posição exibe todas as métricas que formaram o score, sem expor e-mail, tokens ou informações administrativas.
