# LEIA ANTES DE EXECUTAR — Gate obrigatório

**Status:** `APROVADO_PARA_IMPLEMENTACAO`  
**Fase autorizada:** implementação completa por marcos  
**Implementação autorizada:** sim  
**Atualizado em:** 31 de julho de 2026

## 1. Finalidade

Este arquivo é o gate obrigatório do PostX. Ele deve ser lido integralmente antes de qualquer ação no repositório.

O proprietário aprovou a documentação e autorizou explicitamente a implementação completa no workspace, na VPS e no Supabase em 31 de julho de 2026.

## 2. O que pode ser feito agora

- Implementar backend, frontend, banco, workers, scheduler, storage, testes e infraestrutura.
- Configurar e operar o projeto Supabase e a VPS autorizados.
- Instalar dependências e serviços necessários.
- Executar migrations, testes, builds e deploys.
- Atualizar a documentação conforme decisões e resultados.

## 3. Limites permanentes

- Não usar automação não oficial do Instagram.
- Não versionar nem exibir segredos.
- Não operar recursos externos fora da VPS e do Supabase colocados em escopo.
- Não ignorar limites, políticas ou revisão da Meta.
- Não executar mudança destrutiva sem resolver e verificar o alvo exato.

## 4. Como a aprovação deve acontecer

A liberação foi concedida pela mensagem:

> “O projeto foi aprovado, pode iniciar. Tem total autorização para fazer e implementar tudo na VPS e no Supabase.”

Na ausência de escolhas diferentes, as opções marcadas como recomendadas foram adotadas. Para `DEC-018`, os defaults iniciais são: recuperação de mídia por 7 dias, logs detalhados por 90 dias, auditoria por 12 meses e conclusão da exclusão do usuário em até 30 dias.

## 5. Regra de segurança

Credenciais nunca serão gravadas em Markdown, código, logs, fixtures, screenshots ou versionamento. App Secret, tokens do Instagram, chaves do Supabase e segredos JWT devem entrar apenas por um mecanismo de secrets aprovado.

## 6. Regra de escopo

A documentação descreve um produto amplo. Aprovar a visão não significa necessariamente autorizar todo o escopo de uma vez. O desenvolvimento deverá seguir marcos e critérios de aceite, começando pelo núcleo validável.

## 7. Regra sobre a Meta

Capacidades, permissões, métricas, formatos, limites, versões e ciclos de token da API da Meta são dependências externas mutáveis. Antes da implementação de cada integração, a documentação oficial vigente deverá ser revalidada. Se uma expectativa do produto não for suportada oficialmente, não será usada automação não oficial; o comportamento será limitado, adaptado ou submetido ao proprietário.

## 8. Checklist do gate

- [x] Ideia original convertida em especificação.
- [x] Requisitos funcionais e não funcionais documentados.
- [x] Arquitetura proposta documentada.
- [x] Modelo de dados conceitual documentado.
- [x] API e fluxos documentados.
- [x] Segurança e isolamento multi-tenant documentados.
- [x] Scheduler, worker e retentativas documentados.
- [x] Interface e critérios responsivos documentados.
- [x] Testes, observabilidade e operação documentados.
- [x] Riscos e decisões pendentes documentados.
- [x] Proprietário revisou a documentação.
- [x] Proprietário delegou as decisões não especificadas às recomendações.
- [x] Proprietário aprovou explicitamente a implementação.

O primeiro marco autorizado é o **Marco 0 — Fundação e risco técnico**, seguido pelos demais marcos sem necessidade de nova autorização, salvo expansão para sistemas não colocados em escopo.
