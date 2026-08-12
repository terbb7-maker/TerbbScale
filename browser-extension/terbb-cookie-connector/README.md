# Terbb Cookie Connector

Extensão local do Chrome usada pela tela **Contas > Conectar com cookie**.

## Instalação

1. Abra `chrome://extensions`.
2. Ative o **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione esta pasta.
5. Atualize a tela de conexão do Terbb Scale.

## Segurança

- aceita somente cookies pertencentes a `instagram.com`;
- ignora cookies do Facebook, DoubleClick e outros domínios;
- mantém a fila em `chrome.storage.session`, que é temporário e não é sincronizado;
- nunca envia cookies ao backend, Supabase ou logs;
- apaga somente cookies do Instagram ao alternar a conta;
- não contorna checkpoint, CAPTCHA ou confirmação adicional da Meta.

O token utilizado pelo Terbb Scale continua sendo obtido exclusivamente pelo Instagram Login oficial.
