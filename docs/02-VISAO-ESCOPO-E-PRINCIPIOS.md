# Visão, escopo e princípios

## 1. Visão

O PostX será um SaaS multi-tenant de alto desempenho para organizar mídias, conectar contas profissionais do Instagram, criar campanhas visuais, calcular agendas e publicar conteúdo automaticamente usando somente a API oficial da Meta com Instagram Login.

## 2. Resultado esperado

Permitir que um usuário aprovado:

1. configure seu próprio Instagram App;
2. conecte uma ou mais contas profissionais;
3. envie e catalogue mídias;
4. monte uma campanha;
5. distribua mídias entre contas;
6. publique imediatamente ou agende;
7. acompanhe execução, falhas, métricas e saúde do sistema.

## 3. Público

- Operadores de múltiplas contas profissionais.
- Agências e equipes de conteúdo.
- Administradores da plataforma.

A definição comercial exata do público, planos e limites permanece pendente.

## 4. Princípios imutáveis

1. **Somente API oficial:** nenhuma automação por navegador, scraping, senha do Instagram ou API privada.
2. **Instagram Login:** não usar Facebook Login no fluxo de conexão de contas.
3. **Isolamento por tenant:** credenciais, contas, mídias, campanhas e logs nunca são compartilhados entre usuários.
4. **Credenciais por usuário:** cada usuário utiliza seu próprio App ID e App Secret.
5. **Backend assíncrono:** rotas de API não aguardam processamento pesado ou publicação.
6. **Worker independente:** falha ou lentidão na execução não deve bloquear a API principal.
7. **Idempotência:** uma mesma publicação lógica não pode ser duplicada por retentativa concorrente.
8. **Auditabilidade:** ações críticas e chamadas de publicação devem ser rastreáveis.
9. **Segurança por padrão:** segredo criptografado, menor privilégio e ausência de tokens em logs.
10. **Experiência rápida:** interface responsiva, feedback imediato e processamento pesado em segundo plano.

## 5. Escopo funcional completo

- Cadastro, aprovação, login, logout e renovação de sessão.
- RBAC customizado.
- Configurações do Instagram App por usuário.
- OAuth com Instagram Login.
- Gerenciamento de contas conectadas.
- Biblioteca de imagens, vídeos, capas e tags.
- Campanhas em rascunho, agendadas, executando, pausadas, concluídas, canceladas ou com falha.
- Publicações Feed, Reel e Story, conforme suporte oficial.
- Estratégias mesma mídia, sequencial e aleatória sem repetição antes de esgotar o conjunto.
- Scheduler, filas, workers, retentativas e renovação de tokens.
- Dashboard agregado e atualização em tempo real.
- Logs operacionais, auditoria e painel administrativo.
- Notificações internas.
- Painel de saúde.

## 6. Não objetivos

- Publicar em contas pessoais não suportadas pela API.
- Contornar revisão do App, permissões, limites ou políticas da Meta.
- Gerenciar mensagens ou comentários, exceto se adicionados posteriormente.
- Automação de curtidas, seguidores ou interações.
- Editor avançado de vídeo/imagem no primeiro ciclo.
- Aplicativo móvel nativo.
- Cobrança real até a definição do provedor e das regras comerciais.

## 7. Stack solicitada

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy 2 assíncrono
- Alembic
- AsyncIO
- APScheduler
- httpx assíncrono
- Pydantic V2
- Redis para fila, locks, cache e eventos
- Celery opcional, sujeito a decisão

### Dados e storage

- Supabase PostgreSQL
- Supabase Storage
- Supabase Auth somente como identidade/autenticação

### Frontend

- React
- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

## 8. Restrições de produto

- A Meta é uma dependência crítica e mutável.
- Arquivos enviados precisam ser compatíveis com os formatos atuais da API.
- Mídias que a Meta buscará por URL precisam ficar acessíveis pelo tempo necessário sem tornar a biblioteca pública de forma permanente.
- “Tempo real” significa atualização em segundos, não garantia hard real-time.
- O scheduler por minuto não assegura execução exata no segundo; a fila deve fazer o refinamento.

## 9. Medida de sucesso inicial

O primeiro sucesso técnico será uma publicação idempotente, rastreável e executada por worker em uma conta de teste profissional, usando Instagram Login, a partir de uma mídia armazenada no Supabase e sem bloquear a API.

