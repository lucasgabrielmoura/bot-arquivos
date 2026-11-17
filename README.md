# bot-arquivos

Bot de Telegram particular que faz as conversões do iLovePDF **localmente**, sem mandar seus arquivos para nenhum site.
Os arquivos ficam só no aparelho que roda o bot, numa pasta temporária apagada logo após cada conversão.
Por padrão qualquer pessoa que encontrar o bot pode usar. Para restringir, preencha `ALLOWED_USERS` no `.env`.

## O que ele faz

| Categoria | Operações |
|---|---|
| Organizar | Juntar, Dividir, Extrair páginas, Remover páginas, Reordenar, Girar |
| Otimizar | Comprimir (3 níveis), Reparar, OCR (PDF pesquisável) |
| Converter **para** PDF | Imagens (JPG/PNG/WEBP...) → PDF, Word/Excel/PowerPoint/ODT/TXT/HTML → PDF |
| Converter **de** PDF | PDF → JPG/PNG, Word, Excel (tabelas), PowerPoint, Texto, PDF/A |
| Editar / Segurança | Marca d'água, Números de página, Cortar margens, Proteger com senha, Desbloquear |

Fica de fora (precisam de editor visual ou de serviço externo): assinar, editar texto, redigir, comparar e traduzir.
O PDF → PowerPoint gera um slide com a imagem de cada página, sem texto editável.

**Como usar:** mande um ou mais arquivos para o bot e escolha a operação no menu que aparece. Os comandos são `/cancelar`, `/limpar`, `/ferramentas` (mostra o que está instalado) e `/meuid`.

## Sobre o número de telefone

Um bot de Telegram **não usa número de telefone**: ele é criado no @BotFather e funciona com um *token*.
O celular do seu amigo só **roda o programa** e precisa de internet. A conta pessoal dele não é usada.

> WhatsApp ficou de fora: lá só existe API oficial paga (Meta Business) ou bibliotecas não oficiais, que podem banir o número.

## 1. Criar o bot (no seu Telegram, 2 min)

1. Abra o **@BotFather**, mande `/newbot`, escolha um nome e um usuário que termine em `bot`.
2. Guarde o **token** (`123456:ABC...`). Ele é a senha do bot, não compartilhe.
3. Recomendado: `/setjoingroups` → **Disable**.

## 2. Instalar no celular Android (Termux)

1. Instale o **Termux pelo F-Droid** (a versão da Play Store está abandonada).
2. No Termux:
   ```bash
   pkg update && pkg install -y proot-distro git
   proot-distro install debian
   proot-distro login debian
   ```
3. Dentro do Debian:
   ```bash
   apt update && apt install -y git
   git clone <URL-DO-SEU-REPO> bot-arquivos   # ou copie a pasta para o celular
   cd bot-arquivos
   bash scripts/instalar-debian.sh
   nano .env        # cole o BOT_TOKEN
   bash scripts/iniciar.sh
   ```
4. Pronto: qualquer pessoa já pode usar. (Opcional, para restringir: mande `/meuid` ao bot, coloque os IDs em `ALLOWED_USERS` separados por vírgula e reinicie.)

A instalação baixa cerca de 1 GB (o LibreOffice é a maior parte). Sem LibreOffice o bot funciona, só fica sem Word/Excel/PPT → PDF; veja em `/ferramentas`.

### Manter rodando 24h

- No Termux, rode `termux-wake-lock` (ou segure a notificação do Termux e toque em *Acquire wakelock*).
- Nas configurações do Android, desative a **otimização de bateria** do Termux.
- Deixe o celular no carregador e no Wi-Fi.
- O `iniciar.sh` reinicia o bot sozinho quando ele cai.
- Para iniciar depois que o celular reinicia, use o app **Termux:Boot** (F-Droid) com um script em `~/.termux/boot/` que rode `proot-distro login debian -- bash -c "cd bot-arquivos && bash scripts/iniciar.sh"`.

## Limites do Telegram

Bots baixam arquivos de até **20 MB** e enviam até **50 MB**. Para ir até 2 GB, rode um [servidor Bot API local](https://github.com/tdlib/telegram-bot-api) e preencha `TELEGRAM_API_URL`. Num celular velho isso costuma ser pesado demais.

## Privacidade

- Nenhum arquivo sai do aparelho, exceto pelo próprio Telegram (que entrega e recebe as mensagens).
- Com `ALLOWED_USERS` vazio o bot é aberto a todos. Cada usuário tem sua própria pasta e só recebe os próprios resultados. Se preencher `ALLOWED_USERS`, quem não estiver na lista recebe só "Acesso negado" e os arquivos nem são baixados.
- Arquivos temporários são apagados depois de cada resultado, em erro, em `/cancelar` e ao iniciar o bot. O log não registra nomes nem conteúdo de arquivos.
- Mensagens com senha (Proteger/Desbloquear) são apagadas do chat pelo bot logo após a leitura.
- Para mais privacidade, ative mensagens temporárias no chat com o bot. Lembre que o Telegram guarda os arquivos enviados na nuvem dele.

## Rodar no PC (testes)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt pytest   # Linux/Mac: .venv/bin/pip
cp .env.example .env    # preencha
python -m bot
python -m pytest -q
```
