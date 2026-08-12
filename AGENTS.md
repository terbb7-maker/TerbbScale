# Instruções obrigatórias para qualquer agente

Este repositório está na fase **IMPLEMENTAÇÃO AUTORIZADA**.

## Regra principal

Antes de ler, criar, alterar, executar ou remover qualquer artefato deste projeto, leia integralmente:

1. [`docs/00-LEIA-ANTES-DE-EXECUTAR.md`](docs/00-LEIA-ANTES-DE-EXECUTAR.md)
2. [`docs/01-INDICE-DA-DOCUMENTACAO.md`](docs/01-INDICE-DA-DOCUMENTACAO.md)
3. [`docs/18-DECISOES-PENDENTES.md`](docs/18-DECISOES-PENDENTES.md)

## Estado atual

- A documentação foi aprovada explicitamente pelo proprietário em 31 de julho de 2026.
- A implementação completa está autorizada no workspace, na VPS e no projeto Supabase indicado pelo proprietário.
- As opções recomendadas em `docs/18-DECISOES-PENDENTES.md` foram adotadas como baseline; exceções futuras devem ser registradas.
- Alterações destrutivas continuam exigindo resolução exata do alvo, validação e registro.
- Credenciais e tokens nunca podem ser versionados ou exibidos em logs.
- A conexão, os tokens, as campanhas e os insights permanecem na API oficial com Instagram Login. A única exceção aprovada é a publicação local e manual do Story predefinido com link durante o fluxo por cookie, isolada na extensão conforme ADR-013.

## Hierarquia documental

Em caso de conflito:

1. A instrução explícita mais recente do proprietário prevalece.
2. O gate em `docs/00-LEIA-ANTES-DE-EXECUTAR.md` prevalece sobre os demais documentos.
3. Decisões aprovadas prevalecem sobre propostas; as recomendações formalmente adotadas são decisões aprovadas.
4. Requisitos de produto prevalecem sobre detalhes técnicos sugeridos.
5. Restrições atuais da API oficial da Meta prevalecem sobre expectativas do produto; a divergência deve ser documentada e levada ao proprietário.
