# Terbb Scale

Terbb Scale é um SaaS multi-tenant para gerenciamento, agendamento e publicação automatizada no Instagram. Conexão, tokens, campanhas e insights usam a **Instagram Platform API com Instagram Login**, sem Facebook Login. Há uma extensão local opcional para preparar sessões por cookie e publicar, por clique, um Story predefinido com link durante a integração de contas. O nome técnico histórico do repositório e de alguns serviços internos permanece `PostX` para evitar mudanças operacionais desnecessárias.

## Situação do projeto

> **NÚCLEO IMPLEMENTADO E PUBLICADO.**

O projeto entrou em implementação em 31 de julho de 2026, após aprovação explícita da documentação e autorização para operar a VPS e o Supabase. A implantação atual está disponível em [postx.179-197-73-32.sslip.io](https://postx.179-197-73-32.sslip.io).

## Leitura obrigatória

Comece por:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/00-LEIA-ANTES-DE-EXECUTAR.md`](docs/00-LEIA-ANTES-DE-EXECUTAR.md)
3. [`docs/01-INDICE-DA-DOCUMENTACAO.md`](docs/01-INDICE-DA-DOCUMENTACAO.md)
4. [`docs/18-DECISOES-PENDENTES.md`](docs/18-DECISOES-PENDENTES.md)

## Componentes em produção

- FastAPI assíncrono com autenticação Supabase, permissões e auditoria;
- Next.js responsivo com dashboard, biblioteca, contas, campanhas, logs e admin;
- PostgreSQL Supabase com 32 tabelas, RLS em todas elas e Storage privado;
- Redis, Celery, scheduler independente, retentativas e renovação de tokens;
- Instagram Login por aplicativo próprio de cada usuário;
- publicação oficial de Feed, Reel e Story;
- preset de Story com link, editor visual completo do adesivo e publicação local opcional no conector por cookie;
- coleta periódica de Insights e atualização do dashboard via WebSocket;
- Caddy com HTTPS automático e headers de segurança.

## Operação

O runtime fica em `/opt/postx` na VPS e é gerenciado por Docker Compose:

```bash
cd /opt/postx
docker compose ps
docker compose logs -f api worker scheduler
```

O arquivo `.env` é ignorado pelo Git e deve permanecer com permissão `0600`.

## Decisões adotadas

As opções recomendadas em [`docs/18-DECISOES-PENDENTES.md`](docs/18-DECISOES-PENDENTES.md) formam o baseline autorizado. Mudanças posteriores serão registradas em [`docs/19-REGISTRO-DE-DECISOES.md`](docs/19-REGISTRO-DE-DECISOES.md).
