# Riscos e mitigações

| ID | Risco | Prob. | Impacto | Mitigação |
|---|---|---:|---:|---|
| R-001 | Meta altera versão, scopes ou formato | Alta | Alto | Adapter versionado, revalidação, testes de contrato e calendário de versões |
| R-002 | App do usuário sem review/configuração correta | Alta | Alto | Wizard, validação, diagnóstico e documentação por App |
| R-003 | Formato desejado não suportado para conta | Média | Alto | Capability detection, matriz versionada e UI indisponível com motivo |
| R-004 | Limites inviabilizam posts/hora | Alta | Alto | Preview aplica limites, rate limiter e aviso de capacidade real |
| R-005 | Token/secret vazado | Média | Crítico | Cifra, secrets manager, redaction, menor privilégio e rotação |
| R-006 | Acesso cruzado entre usuários | Média | Crítico | Tenant scope, RLS, policies e testes negativos |
| R-007 | Publicação duplicada após retry/crash | Média | Crítico | Idempotência, persistência de IDs externos, lease e reconciliação |
| R-008 | Meta publicou, banco não confirmou | Média | Alto | Estado intermediário, reconciliação e bloqueio de retry cego |
| R-009 | Redis cai/perde dados | Média | Alto | PostgreSQL como fonte, replay do dispatcher e filas reconstruíveis |
| R-010 | Scheduler duplicado | Média | Alto | Leader/lease, lock por campanha e constraints únicas |
| R-011 | Explosão de jobs em campanha grande | Média | Alto | Horizonte de planejamento, lotes, quotas e backpressure |
| R-012 | URL de mídia expira durante processamento | Média | Alto | TTL suficiente, renovação/proxy e teste real |
| R-013 | Supabase pool esgotado | Média | Alto | Budget global, pooler, transações curtas e métricas |
| R-014 | Upload malicioso ou mídia-bomba | Média | Alto | Inspeção, limites, sandbox de processamento e scanning |
| R-015 | Métrica exibida incorretamente | Alta | Médio | Catálogo semântico, `null`, source/version e testes |
| R-016 | Timezone/DST gera horário errado | Média | Alto | UTC, timezone IANA, validação de ambiguidades e testes |
| R-017 | Python 3.13 incompatível com dependência | Média | Médio | Spike e matriz de versões antes de congelar stack |
| R-018 | Celery conflita com modelo async | Média | Médio | Benchmark/spike; opção Redis Streams |
| R-019 | Dashboard sobrecarrega banco | Média | Médio | Agregados, cache, índices e limites de série |
| R-020 | Custos de storage/egress/logs | Média | Alto | Quotas, lifecycle, thumbnails e retenção por plano |
| R-021 | Usuário troca App e invalida contas | Média | Alto | Alertas, versionamento de config e reconexão guiada |
| R-022 | Suspensão deixa posts sendo executados | Média | Alto | Evento de revogação, cancelamento e check antes de publicar |
| R-023 | Falha de aprovação/admin abuse | Baixa | Crítico | MFA, reauth, RBAC, auditoria e alertas |
| R-024 | Escopo inicial grande atrasa validação | Alta | Alto | Marcos, MVP vertical e gates de aceite |
| R-025 | Política da Meta proíbe caso de uso específico | Média | Crítico | Revisão de políticas e App Review antes de comercializar |
| R-026 | Export de cookies vaza ou restaura sessão incorreta | Média | Crítico | Processamento somente na extensão, domínio allowlisted, memória de sessão, fila mascarada, limpeza explícita e proibição em logs/backend |
| R-027 | Meta invalida cookies ou exige checkpoint | Alta | Médio | Informar falha, abrir login normal e nunca contornar desafio, CAPTCHA ou confirmação adicional |
| R-028 | Instagram altera endpoints privados de Story/link | Alta | Alto | Adapter mínimo isolado na extensão, erro sanitizado, sem retry cego, versão da extensão e kill switch |
| R-029 | Renderização de vídeo com edição consome memória/CPU local | Média | Médio | FFmpeg/WASM somente após clique, preset limitado a 60 s/100 MB, preset `ultrafast`, limpeza dos arquivos temporários e timeout explícito |
| R-029 | Story é publicado na conta errada ou duplicado | Média | Crítico | Conferir `ds_user_id` da fila, exigir clique por publicação, manter estado local e nunca repetir automaticamente após resposta ambígua |
| R-030 | URL do Story aponta para destino incorreto ou inseguro | Média | Alto | Exigir HTTPS sem credenciais, preview do hostname, título limitado e auditoria somente do hostname |

## Riscos aceitos nesta fase

A implementação está autorizada. O proprietário aceitou o risco operacional do conector local de cookies e dos endpoints privados usados somente para o Story com link em 12 de agosto de 2026, condicionado aos controles dos ADR-012/013; vazamento, persistência remota, login automático, publicação silenciosa ou contorno de proteções da Meta não foram aceitos.

## Kill switches necessários

- por ambiente;
- por Instagram App;
- por tenant;
- por conta;
- por campanha;
- por tipo de operação.

Kill switch pausa novos jobs; não desfaz publicação já aceita pela Meta.
