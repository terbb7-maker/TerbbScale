# Frontend, UX e design system

## 0. Identidade Terbb Scale

- nome público: **Terbb Scale**;
- marca oficial fornecida pelo proprietário, com símbolo roxo sobre azul-marinho quase preto;
- landing page pública removida: `/` redireciona para `/login`;
- login e cadastro são as únicas telas públicas de entrada;
- referências visuais: sidebar escura, superfícies bem delimitadas, cantos arredondados e realce roxo, sem copiar marcas ou assets de terceiros.

## 1. Direção visual

Tema escuro, premium e minimalista, com fundo azul-marinho/preto e roxo da marca como destaque.

Princípios:

- hierarquia tipográfica clara;
- densidade controlada;
- contraste acessível;
- bordas e elevação discretas;
- cor de destaque usada com parcimônia;
- animações suaves e funcionais;
- estados de loading sem layout shift.

## 2. Estrutura global

### Desktop

- sidebar recolhível;
- command/search;
- header contextual;
- área de conteúdo;
- central de notificações;
- status operacional discreto.

### Mobile

- navegação inferior ou drawer;
- ações primárias ao alcance;
- tabelas viram cards/listas;
- seleções em lote usam action bar fixa;
- formulários sem scroll horizontal.

## 3. Rotas/telas

```text
/login
/pending
/dashboard
/accounts
/media
/campaigns
/campaigns/new
/campaigns/{id}
/logs
/settings
/notifications
/admin/users
/admin/approvals
/admin/plans
/admin/logs
/admin/health
```

## 4. Dashboard

### Hierarquia simplificada

- hero curto com uma única ação principal: criar campanha;
- quatro KPIs operacionais: publicações hoje, campanhas ativas, contas conectadas e fila;
- gráfico de ritmo de publicação;
- engajamento com filtros de período;
- no máximo cinco próximas publicações no primeiro olhar;
- métricas avançadas de proxy permanecem na tela de Proxies, não na dashboard.

### Painéis

- próximas publicações;
- campanhas agora;
- últimos logs;
- erros recentes;
- publicações/dia;
- views/dia;
- crescimento;
- uso de contas.

Cada card mostra período, timezone e estado `unavailable` quando não há métrica.

O painel de Engajamento possui seletor segmentado Hoje, Ontem, Mês e Personalizado. Personalizado abre dois campos de data, impede intervalo invertido/futuro e mantém a atualização por WebSocket para o filtro ativo.

## 5. Contas

- grid/lista com foto, nome, username, ID mascarável, status, expiração, posts e última publicação;
- token nunca aparece; mostrar somente estado/expiração;
- conectar, reconectar, verificar, atualizar token quando suportado e remover;
- seleção individual, página, filtro inteiro e em lote;
- barra contextual para remover até 200 contas selecionadas;
- avisos sobre conta profissional, scopes e App do usuário.
- resumo de contas disponíveis e que precisam de atenção;
- badge de situação operacional, confiança, última verificação, último sucesso, falhas consecutivas e ação recomendada;
- ação “Testar situação agora” e histórico recente com códigos sanitizados da Meta;
- atualização por WebSocket `account.health_updated`, com polling de segurança quando o socket estiver indisponível.
- ação secundária “Conectar com cookie”, preservando como principal o Instagram Login existente;
- tela separada com instalação/detecção da extensão, preset de mídia/link, importação múltipla de JSON, fila mascarada e etapas ativar sessão, postar Story, abrir convites, conectar via OAuth e próxima conta;
- seletor de mídia pronta e editor 9:16 com arraste, quatro alças de tamanho, alça/slider de rotação, posição numérica, 12 fontes, itálico, tamanho e paletas de texto/fundo;
- preview deve reproduzir título/hostname, ícone, truncamento, fonte, cores e geometria que serão renderizados localmente; a fila mantém estado por conta (`idle`, publicando, publicado ou falha sanitizada);
- nenhum valor de cookie, senha ou 2FA é renderizado, enviado à API ou mantido após o encerramento da sessão da extensão.

## 6. Biblioteca

- dropzone e seletor múltiplo;
- fila de uploads com progresso individual;
- grid virtualizado com preview;
- filtros persistíveis;
- busca;
- seleção em lote;
- remoção em massa com barra contextual e confirmação;
- painel de detalhe com metadados, tags e compatibilidade;
- estados skeleton, vazio, erro, processando e falha parcial.

## 7. Construtor de campanha

Fluxo visual proposto:

1. detalhes;
2. tipo e conteúdo;
3. contas;
4. mídias;
5. estratégia;
6. frequência e duração;
7. data/timezone;
8. capa;
9. preview do plano;
10. validação e ativação.

Rascunho é salvo sem exigir formulário completo. O preview deve mostrar pares conta/mídia/horário e avisos de limite/repetição.

## 8. Logs

- tabela densa com conta, campanha, mídia, horário, duração, status e erro;
- filtros combináveis;
- drawer de detalhe;
- resposta externa sanitizada e recolhida por padrão;
- copy de request/correlation ID;
- atualização ao vivo sem deslocar a leitura do usuário.

## 9. Admin

- KPIs globais;
- fila de aprovações como ação primária;
- tabelas com filtros e paginação;
- modais de confirmação para ações destrutivas;
- motivo obrigatório para suspensão/rejeição;
- saúde por componente sem expor segredos.

## 10. Estados obrigatórios

Todo fluxo terá:

- initial/loading;
- success;
- empty;
- validation error;
- permission denied;
- network/provider error;
- partial success;
- stale/offline;
- retrying;
- disabled com explicação.

## 11. Responsividade

Breakpoints serão guiados pelo conteúdo. Critérios:

- funcional a partir de 320 px;
- alvos de toque adequados;
- sem overflow horizontal acidental;
- gráficos com resumo textual;
- upload e criação de campanha utilizáveis por toque;
- ações em lote não dependem de hover.

## 12. Acessibilidade

- WCAG 2.2 AA como meta.
- navegação por teclado;
- foco visível;
- labels e descrições de erro;
- contraste;
- `prefers-reduced-motion`;
- status não comunicado apenas por cor;
- modais com focus trap;
- live regions para progresso/notificações relevantes.

## 13. Performance percebida

- Server Components onde contribuírem.
- Client Components somente para interação.
- paginação/virtualização.
- thumbnails adequadas.
- optimistic UI apenas em ações reversíveis.
- prefetch seletivo.
- budgets de bundle e Web Vitals no plano de qualidade.

## 14. Design tokens

Tokens semânticos para background, surface, border, text, muted, accent, success, warning e destructive. Nada de cores hardcoded dispersas. Componentes shadcn/ui serão adaptados a esses tokens.
# Tela Proxies

O menu inclui Proxies. A tela fornece cadastro, edição, exclusão protegida individual/em massa, teste individual/em massa e colunas de IP, protocolo, status, latência, última verificação e uso.

A tela também possui “Importar lista”: uma área de texto aceita uma linha ou várias no formato `host:porta:usuário:senha`, permite escolher o protocolo e mostra somente números de linha e motivos de rejeição. O resultado de teste exibe uma mensagem direta para erro de configuração, indisponibilidade ou timeout, em vez de erro interno.

A rotação é configurada somente dentro de cada campanha. A tela de Contas não expõe configuração de proxy.

# Tela de ranking mensal

O cartão promocional inferior da sidebar é substituído pelo botão **Ranking mensal**. A página `/app/ranking` oferece seletor de mês, período oficial, quantidade de participantes, posição do usuário atual, pódio e classificação detalhada. Cada pessoa exibe o score e todas as métricas em cartões legíveis no desktop e no mobile. Não existem abas ou filtros por categoria.
