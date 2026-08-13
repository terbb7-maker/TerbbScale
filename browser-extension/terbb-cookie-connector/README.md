# Terbb Cookie Connector

Extensão local do Chrome usada pela tela **Contas > Conectar com cookie**.

## Instalação

1. Abra `chrome://extensions`.
2. Ative o **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione esta pasta.
5. Atualize a tela de conexão do Terbb Scale.

Se a extensão já estava instalada, clique em **Recarregar** no cartão dela em
`chrome://extensions` e depois atualize a página do Terbb Scale. A versão mínima
para publicação de Story é **1.2.1**.

## Segurança

- aceita somente cookies pertencentes a `instagram.com`;
- ignora cookies do Facebook, DoubleClick e outros domínios;
- mantém a fila em `chrome.storage.session`, que é temporário e não é sincronizado;
- nunca envia cookies ao backend, Supabase ou logs;
- publica o Story predefinido somente após clique no Terbb Scale e confirmação do `ds_user_id` ativo;
- renderiza localmente posição, tamanho, rotação, fonte, itálico e cores do adesivo de link;
- mantém as 12 fontes e a paleta do editor original dentro da própria extensão;
- baixa o original por URL assinada de cinco minutos diretamente do projeto Supabase;
- captura e usa CSRF/headers do Instagram somente dentro da extensão;
- apaga somente cookies do Instagram ao alternar a conta;
- não contorna checkpoint, CAPTCHA ou confirmação adicional da Meta.

O publicador de Story com link usa endpoints privados do Instagram e pode deixar de funcionar quando a interface web mudar. O token utilizado pelo Terbb Scale, as campanhas e os insights continuam no Instagram Login/API oficial.

Vídeos precisam ser renderizados localmente com FFmpeg antes do upload e, por isso, podem levar alguns minutos em computadores mais lentos. Nenhuma mídia é enviada a um serviço de renderização externo.
