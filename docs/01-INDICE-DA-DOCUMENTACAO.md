# Índice da documentação

## Ordem recomendada de leitura

| Ordem | Documento | Finalidade |
|---:|---|---|
| 0 | [`00-LEIA-ANTES-DE-EXECUTAR.md`](00-LEIA-ANTES-DE-EXECUTAR.md) | Gate obrigatório e estado da autorização |
| 1 | [`02-VISAO-ESCOPO-E-PRINCIPIOS.md`](02-VISAO-ESCOPO-E-PRINCIPIOS.md) | Objetivo, público, escopo e princípios |
| 2 | [`03-REQUISITOS-FUNCIONAIS.md`](03-REQUISITOS-FUNCIONAIS.md) | Comportamentos por módulo |
| 3 | [`04-REGRAS-DE-NEGOCIO.md`](04-REGRAS-DE-NEGOCIO.md) | Estados, distribuição, agendamento e métricas |
| 4 | [`05-ARQUITETURA-DO-SISTEMA.md`](05-ARQUITETURA-DO-SISTEMA.md) | Componentes e responsabilidades |
| 5 | [`06-MODELO-DE-DADOS.md`](06-MODELO-DE-DADOS.md) | Entidades, relações e isolamento |
| 6 | [`07-API-E-CONTRATOS.md`](07-API-E-CONTRATOS.md) | Convenções e endpoints |
| 7 | [`08-INTEGRACAO-OFICIAL-INSTAGRAM.md`](08-INTEGRACAO-OFICIAL-INSTAGRAM.md) | OAuth, publicação, tokens e limitações |
| 8 | [`09-SCHEDULER-WORKERS-E-FILAS.md`](09-SCHEDULER-WORKERS-E-FILAS.md) | Motor de execução independente |
| 9 | [`10-BIBLIOTECA-DE-MIDIA-E-STORAGE.md`](10-BIBLIOTECA-DE-MIDIA-E-STORAGE.md) | Upload, metadados e ciclo de mídia |
| 10 | [`11-AUTENTICACAO-AUTORIZACAO-E-ADMIN.md`](11-AUTENTICACAO-AUTORIZACAO-E-ADMIN.md) | Supabase Auth, aprovação e RBAC |
| 11 | [`12-FRONTEND-UX-E-DESIGN-SYSTEM.md`](12-FRONTEND-UX-E-DESIGN-SYSTEM.md) | Telas, estados e responsividade |
| 12 | [`13-SEGURANCA-PRIVACIDADE-E-AUDITORIA.md`](13-SEGURANCA-PRIVACIDADE-E-AUDITORIA.md) | Controles de segurança |
| 13 | [`14-PERFORMANCE-ESCALABILIDADE-E-CONFIABILIDADE.md`](14-PERFORMANCE-ESCALABILIDADE-E-CONFIABILIDADE.md) | Metas e desenho para escala |
| 14 | [`15-OBSERVABILIDADE-E-OPERACAO.md`](15-OBSERVABILIDADE-E-OPERACAO.md) | Logs, métricas, alertas e saúde |
| 15 | [`16-TESTES-E-QUALIDADE.md`](16-TESTES-E-QUALIDADE.md) | Estratégia de validação |
| 16 | [`17-PLANO-DE-ENTREGA-E-ACEITE.md`](17-PLANO-DE-ENTREGA-E-ACEITE.md) | Marcos e critérios de aceite |
| 17 | [`18-DECISOES-PENDENTES.md`](18-DECISOES-PENDENTES.md) | Escolhas que exigem aprovação |
| 18 | [`19-REGISTRO-DE-DECISOES.md`](19-REGISTRO-DE-DECISOES.md) | Histórico de decisões |
| 19 | [`20-RISCOS-E-MITIGACOES.md`](20-RISCOS-E-MITIGACOES.md) | Riscos técnicos, externos e de produto |
| 20 | [`21-MATRIZ-DE-RASTREABILIDADE.md`](21-MATRIZ-DE-RASTREABILIDADE.md) | Relação entre pedido, especificação e aceite |
| 21 | [`22-GLOSSARIO.md`](22-GLOSSARIO.md) | Vocabulário comum |
| 22 | [`23-REFERENCIAS-EXTERNAS.md`](23-REFERENCIAS-EXTERNAS.md) | Fontes oficiais e data de validação |

## Legenda de status

- **Requisito:** solicitado pelo proprietário.
- **Proposta:** interpretação ou desenho recomendado, ainda revisável.
- **Pendente:** exige escolha do proprietário ou validação externa.
- **Restrição externa:** comportamento imposto por um serviço utilizado.
- **Fora do MVP:** possível evolução, não incluída no primeiro marco.

## Regra de atualização

Uma mudança de requisito deve atualizar, quando aplicável:

1. requisitos funcionais;
2. regras de negócio;
3. modelo de dados;
4. contratos da API;
5. critérios de aceite;
6. matriz de rastreabilidade;
7. registro de decisões.

