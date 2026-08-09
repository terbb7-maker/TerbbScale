# Regras de negócio

## 1. Multi-tenancy

- O tenant inicial é o usuário proprietário; a evolução para organizações/equipes é uma decisão pendente.
- Toda entidade de negócio contém `owner_id` ou vínculo equivalente não anulável.
- Toda consulta deve aplicar escopo de tenant no servidor; IDs enviados pelo cliente nunca bastam como autorização.
- Uma conta, mídia, campanha ou credencial de um tenant não pode ser referenciada por outro.

## 2. Estados do usuário

```text
pending -> active -> suspended -> active
pending -> rejected
active|suspended|rejected -> deleted
```

- `pending`: cadastro existe, mas APIs e UI protegidas negam acesso.
- `active`: acesso conforme permissões.
- `suspended`: acesso e renovação de sessão revogados.
- `rejected`: cadastro não aprovado.
- `deleted`: exclusão lógica durante retenção e posterior anonimização/remoção.

## 3. Estados da conta do Instagram

```text
connecting -> connected
connecting -> error
connected -> expiring -> expired
connected|expiring -> revoked
expired|revoked|error -> reconnecting -> connected
* -> removed
```

Uma conta só é elegível para novas publicações se estiver `connected`, possuir os scopes necessários e não estiver bloqueada por limite conhecido.

O estado de conexão é separado da situação operacional (`health_status`). A situação pode ser `unknown`, `checking`, `operational`, `reauth_required`, `action_required`, `permission_required`, `temporarily_restricted`, `possibly_suspended` ou `provider_unavailable`. Uma resposta oficial bem-sucedida confirma `operational`; erros documentados confirmam apenas a classe que efetivamente representam. Como a API oficial não expõe um campo geral de suspensão ou desafio antirrobô, `possibly_suspended` é sempre uma inferência após falhas repetidas e deve orientar o usuário a confirmar no aplicativo do Instagram.

`reauth_required`, `action_required`, `permission_required`, `temporarily_restricted` e `possibly_suspended` bloqueiam novas publicações. Jobs já planejados são reagendados, sem gastar tentativas, até uma verificação oficial bem-sucedida ou reconexão. Falha de rede, rate limit ou indisponibilidade da Meta não comprova recuperação e nunca remove um bloqueio anterior.

## 4. Estados da mídia

```text
uploading -> processing -> ready
uploading|processing -> failed
ready -> archived
ready|archived -> deleting -> deleted
```

`ready` não significa compatível com todos os formatos. A compatibilidade é derivada de tipo, codec, dimensões, duração e regras atuais da Meta.

## 5. Estados da campanha

```text
draft -> validating -> scheduled -> running -> completed
validating -> draft (com erros)
scheduled|running -> paused -> scheduled|running
draft|scheduled|paused|running -> cancelled
running -> completed_with_errors
running -> failed
```

- Editar campos que alteram o plano de uma campanha `scheduled` exige gerar uma nova versão do plano.
- Uma campanha `running` não pode reescrever jobs já concluídos ou em execução.
- Cancelamento impede novos jobs, mas uma chamada já enviada à Meta pode terminar.

## 6. Estados do job de publicação

```text
planned -> queued -> claimed -> publishing -> succeeded
claimed|publishing -> retry_scheduled -> queued
claimed|publishing -> failed_permanent
claimed|publishing -> dead_letter
planned|queued|retry_scheduled -> cancelled
```

Cada job possui uma chave de idempotência determinística. A publicação externa bem-sucedida é considerada final mesmo se uma atualização local falhar; a reconciliação deve consultar/usar o identificador externo antes de tentar republicar.

## 7. Cálculo de agenda

### Interpretação aprovada

`posts_per_hour` significa a quantidade por conta selecionada, conforme decisão direta do proprietário em 31 de julho de 2026.

Para `P` posts por hora, `H` horas e `C` contas:

- capacidade nominal: `P × H × C` jobs;
- intervalo base: `3600 / P` segundos;
- cada conta recebe `P × H` publicações planejadas;
- cada horário é calculado no timezone da campanha e armazenado em UTC;
- o total real é limitado por contas elegíveis, mídias disponíveis, regras de repetição e limites externos.

O preview deve mostrar quantos jobs serão criados e por que o total pode ser menor.

### Publicar agora

“Agora” significa iniciar o planejamento imediatamente e enfileirar os primeiros jobs elegíveis; não promete publicação síncrona na resposta HTTP.

### Agendar

Datas inexistentes ou ambíguas por horário de verão devem ser rejeitadas ou exigir escolha explícita. Datas passadas são inválidas, salvo uma tolerância operacional pequena e documentada.

## 8. Distribuição de contas

- Contas são ordenadas por uma posição persistida no snapshot da campanha.
- A distribuição padrão usa round-robin para evitar concentrar jobs em uma única conta.
- Uma conta inelegível é pulada e registrada; o comportamento de redistribuir seu job é configurável e inicialmente proposto como “redistribuir se não violar limites”.

## 9. Estratégias de mídia

### Mesma mídia (`same_media`)

Uma mídia principal é usada para todas as contas selecionadas. Se houver múltiplas publicações por conta na mesma campanha, a repetição precisa de confirmação explícita no preview.

### Sequencial (`sequential`)

Cada conta mantém sua própria sequência sobre a ordem do snapshot:

- a posição inicial usa a posição da conta no snapshot, preservando a distribuição inicial conta 1/mídia 1, conta 2/mídia 2 etc.;
- a publicação seguinte da mesma conta avança para a próxima mídia;
- nenhuma conta fica presa à mesma mídia por causa do round-robin global;
- ao esgotar mídias, cada conta reinicia sua sequência somente se repetição estiver permitida;
- sem repetição, cada conta recebe no máximo uma publicação por mídia selecionada.

### Aleatória sem reposição (`random_without_replacement`)

- O sistema embaralha uma cópia independente do conjunto de mídias para cada conta e ciclo.
- Nenhuma mídia se repete para a mesma conta antes de todas serem usadas por ela.
- Para permitir reprodução e auditoria, o seed é persistido no snapshot e reutilizado entre preview e ativação.
- Ao esgotar o conjunto, inicia-se um novo ciclo embaralhado por conta apenas se a campanha permitir repetição; com mais de uma mídia, a fronteira entre ciclos não repete imediatamente a última mídia do ciclo anterior.

### Ordem de execução por conta

Cada job persiste `plan_position`. Dentro da mesma versão de campanha e conta, um job só pode publicar depois que todos os predecessores dessa conta alcançarem estado final. O worker usa lock distribuído por conta e o dispatcher ordena por horário, rodada e posição do plano; paralelismo entre contas continua permitido.

## 10. Legenda e hashtags

- A legenda final é composta no backend a partir de legenda e hashtags normalizadas.
- O preview deve mostrar exatamente o texto a publicar.
- Limites e caracteres aceitos devem usar regras atuais por formato.
- Story pode não aceitar legenda no mesmo sentido de Feed/Reel; o campo será ignorado somente com aviso explícito.

## 11. Capa

- `automatic`: Instagram seleciona conforme comportamento suportado.
- `custom`: usuário envia/seleciona capa e visualiza preview.
- A opção será exibida apenas para formatos e endpoints que aceitam capa customizada.
- Uma campanha inválida por capa incompatível não pode ser ativada.

## 12. Retentativas

Falhas temporárias incluem, conforme classificação:

- HTTP 429;
- timeout e falha transitória de rede;
- HTTP 5xx;
- processamento de container ainda não concluído.

Falhas permanentes incluem:

- token revogado sem possibilidade de renovação;
- permissão ausente;
- mídia inválida;
- conta/formato não suportado;
- erro de validação da campanha.

Backoff proposto: exponencial com jitter, limite de tentativas e respeito a `Retry-After`. Valores exatos pertencem à configuração operacional.

## 13. Métricas

- Métricas externas são snapshots e podem chegar com atraso.
- Ausência de uma métrica é `null/unavailable`, nunca zero por padrão.
- Engajamento médio precisa de fórmula aprovada.
- Os períodos Hoje, Ontem e Mês usam o calendário e o timezone configurado pelo usuário; o período personalizado inclui integralmente as duas datas informadas e é limitado inicialmente a 366 dias.
- Como os insights oficiais são cumulativos por publicação, o filtro seleciona as publicações feitas no período e soma o snapshot mais recente de cada métrica dessas publicações. Ele não afirma que as interações aconteceram dentro do período.
- A proposta inicial por publicação é:

```text
(curtidas + comentários + compartilhamentos + salvamentos) / alcance × 100
```

Se alcance não estiver disponível ou for zero, o resultado é indisponível. Outras fórmulas devem ser nomeadas e não misturadas.

## 14. Exclusão

- Remover uma conexão revoga ou descarta tokens quando possível e cancela jobs futuros da conta.
- Excluir mídia em uso deve ser bloqueado ou adiado.
- Excluir usuário exige revogação de sessões, cancelamento de jobs e política de retenção.
- Audit logs necessários para conformidade não devem ser silenciosamente apagados; devem ser anonimizados conforme política.
# Regras de proxy

- Proxy é opcional: ausência de proxy sempre significa conexão direta.
- Cada conta pode possuir várias associações ativas em `account_proxies`, ordenadas por prioridade.
- Campanha com proxy exige uma proxy ativa do próprio usuário. Nos modos de rotação, a mesma proxy atende todas as contas da rodada e muda por rodada ou após X rodadas. Sem proxy saudável, a publicação é reagendada e nunca muda silenciosamente para conexão direta.
- O modo `per_post` troca antes de cada post; `every_n_posts` mantém a proxy por X posts e então rotaciona. Uma publicação já iniciada mantém a mesma proxy em todas as etapas.
- Falhas de transporte aplicam cooldown exponencial à proxy e a próxima tentativa exclui aquela proxy quando houver alternativa saudável. Limites retornados pela Meta continuam sujeitos ao backoff normal e não são tratados como mecanismo para burlar rate limits.

# Ranking mensal da comunidade

- O calendário oficial do ranking é `America/Sao_Paulo`.
- O mês atual permanece em andamento até o último instante do último dia; meses futuros são rejeitados.
- Apenas jobs em estado `succeeded` e usuários ativos/não excluídos participam.
- Publicações são contadas por job concluído; métricas usam o snapshot cumulativo mais recente de cada mídia publicada no mês.
- Engajamento segue `(likes + comments + shares + saves) / reach * 100`.
- Score geral: `posts + views + likes + comments + shares + saves + engagement_rate`.
- Empates são resolvidos por views, interações, publicações e identificador estável.
- A resposta inclui os cem primeiros e também o usuário atual caso ele esteja fora desse recorte.
