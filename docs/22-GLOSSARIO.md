# Glossário

- **API principal:** processo FastAPI que atende requisições; não executa publicação pesada.
- **App do usuário / BYO App:** Instagram App configurado e pertencente ao usuário do PostX.
- **Campanha:** definição de conteúdo, contas, estratégia e janela de publicação.
- **Campaign version:** snapshot imutável usado para criar jobs.
- **Capability:** função efetivamente suportada pela conta, scopes, App e versão da API.
- **Container:** recurso intermediário criado na API do Instagram antes da publicação.
- **Dead-letter:** job que esgotou retentativas automáticas e requer ação/reconciliação.
- **Feed:** publicação no feed; subtipo exato depende do formato suportado.
- **Idempotência:** propriedade que evita repetir um efeito ao processar novamente o mesmo comando.
- **Instagram Login:** fluxo direto da Instagram Platform API, sem Facebook Login.
- **Job:** uma publicação planejada para uma conta, mídia e horário.
- **Lease:** reserva temporária com expiração usada por scheduler/worker.
- **Media ID externo:** identificador da mídia publicada retornado pela Meta.
- **Métrica indisponível:** dado que a API não retornou/não suporta; diferente de zero.
- **Outbox:** tabela transacional de eventos ainda não entregues.
- **Owner/tenant:** limite de propriedade e isolamento de dados.
- **Planner:** componente que transforma campanha em jobs.
- **Rate limit:** limite de chamadas/operações imposto interna ou externamente.
- **Reel:** formato de vídeo curto conforme capacidades atuais da plataforma.
- **RLS:** Row Level Security do PostgreSQL.
- **Scope:** permissão solicitada no OAuth.
- **Story:** publicação efêmera, sujeita às capacidades da conta/API.
- **Supabase service role:** credencial privilegiada exclusiva do backend; nunca enviada ao navegador.
- **Tenant isolation:** garantia de que um usuário não acessa recursos de outro.
- **Worker:** processo independente que executa tarefas em segundo plano.

