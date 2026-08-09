# Decisões aprovadas como baseline

**Status:** recomendações adotadas por delegação do proprietário em 31 de julho de 2026.

As opções **A — Recomendado** foram aprovadas para `DEC-001` a `DEC-017`, `DEC-019` e `DEC-020`. Em `DEC-006`, Celery + Redis será usado após validação de compatibilidade; Redis Streams permanece o fallback aprovado.

## Bloqueadoras para o núcleo

### DEC-001 — Modelo de tenant

- **A — Recomendado:** cada usuário é um tenant no MVP; equipes/organizações depois.
- **B:** organizações e membros já no MVP.

Impacto: modelo de dados, RBAC, billing e UX.

### DEC-002 — Sessão JWT/refresh

- **A — Recomendado:** usar access JWT/refresh do Supabase Auth e status/RBAC no PostX.
- **B:** trocar por JWT/refresh próprios do PostX.

Impacto: complexidade, revogação e uso das tabelas `sessions`/`refresh_tokens`.

### DEC-003 — Significado de “posts por hora”

- **B — Aprovado pelo proprietário em 31 de julho de 2026:** quantidade por conta selecionada.
- **A — Substituído:** total da campanha somando todas as contas.

Exemplo: 10 posts/hora com 20 contas significa 10 posts totais ou 200?

### DEC-004 — Quantidade total quando faltam mídias

- **A — Recomendado:** repetir somente após esgotar todas, exibindo aviso e exigindo confirmação.
- **B:** limitar a campanha ao número de mídias únicas.
- **C:** falhar a validação.

### DEC-005 — Estratégia “mesma mídia”

- **A — Recomendado:** uma mídia escolhida explicitamente para todas as contas.
- **B:** a primeira mídia selecionada automaticamente.
- **C:** permitir um conjunto, usando a mesma mídia por rodada.

### DEC-006 — Worker/fila

- **A — Recomendado condicional:** Celery + Redis se a compatibilidade Python 3.13 e os requisitos forem confirmados.
- **B:** worker AsyncIO próprio + Redis Streams.
- **C:** outra fila a definir.

### DEC-007 — Times e precisão

- **A — Recomendado:** scheduler descobre a cada minuto; dispatcher/queue executa no segundo planejado, com SLO de 60 s.
- **B:** precisão diferente; informar tolerância.

### DEC-008 — Feed no MVP

“Feed” inclui:

- **A — Recomendado:** imagem única e vídeo conforme API atual; carousel depois.
- **B:** incluir carousel no MVP.

### DEC-009 — Insights e engajamento

- **A — Recomendado:** `(likes + comments + shares + saves) / reach`.
- **B:** dividir por seguidores.
- **C:** apresentar múltiplas taxas nomeadas.

### DEC-010 — Dados completos da resposta da Meta

- **A — Recomendado:** armazenar versão sanitizada e limitada; payload bruto somente em observabilidade protegida com retenção curta.
- **B:** armazenar payload bruto cifrado no banco.

Guardar “resposta completa” literalmente aumenta risco de segredo/PII.

## Produto e operação

### DEC-011 — Usuário pendente

- **A — Recomendado:** autentica identidade, mas é redirecionado a `/pending` e APIs negam acesso.
- **B:** bloquear emissão de sessão via mecanismo Supabase, mantendo checagem no backend.

### DEC-012 — Suspensão com jobs futuros

- **A — Recomendado:** pausar/cancelar todos os jobs não iniciados.
- **B:** permitir campanhas já agendadas continuarem.

### DEC-013 — Remoção de conta

- **A — Recomendado:** soft delete + tentativa de revogação + cancelamento dos jobs futuros.
- **B:** remoção física imediata, preservando logs anonimizados.

### DEC-014 — Normalização/transcodificação

- **A — Recomendado:** validar e rejeitar incompatíveis no MVP.
- **B:** normalizar automaticamente com FFmpeg desde o MVP.

### DEC-015 — Duplicidade de mídia

- **A — Recomendado:** avisar e oferecer reutilizar o item existente.
- **B:** permitir duplicata silenciosamente.
- **C:** bloquear.

### DEC-016 — Plano/cobrança

- **A — Recomendado:** modelar planos/limites, sem cobrança no MVP.
- **B:** incluir cobrança; informar provedor, moeda e regras.

### DEC-017 — Notificações externas

- **A — Recomendado:** toast + central interna no MVP.
- **B:** incluir e-mail.
- **C:** incluir outros canais.

### DEC-018 — Exclusão e retenção

Defaults aprovados:

- recuperação de mídia: 7 dias;
- logs detalhados: 90 dias;
- auditoria: 12 meses;
- conclusão da exclusão de usuário: até 30 dias.

### DEC-019 — MFA de admin

- **A — Recomendado:** obrigatório antes de produção.
- **B:** recomendado, não obrigatório.

### DEC-020 — Contas Creator e Stories

- **A — Recomendado:** habilitar por capability detectada; se a API não suportar para a conta, mostrar indisponível.
- **B:** restringir Stories a Business desde a UI.

## Dependências externas a validar, não escolhas livres

- versão da Graph API;
- scopes para insights;
- formatos e limites;
- tokens/renovação;
- capas;
- limites de publicação/rate limit;
- App Review e modo Live;
- compatibilidade de bibliotecas com Python 3.13.

## Alterações futuras

Qualquer substituição deve ser registrada como ADR e atualizar requisitos, modelo de dados, API e aceite quando aplicável.
