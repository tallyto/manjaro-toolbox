# Manjaro Toolbox

Interface local para organizar comandos de manutenção, limpeza e instalação no Manjaro/Arch. Ela permite selecionar pacotes visualmente e informar a senha sudo para instalar os itens escolhidos.

O projeto foi criado para deixar em um só lugar os comandos que usamos para:

- limpar cache do Pacman e AUR;
- listar e remover pacotes órfãos;
- instalar ferramentas úteis de terminal;
- instalar apps de mídia, desenvolvimento, backup e rede;
- documentar o que foi removido ou mantido fora do menu.

## Como Rodar

```bash
cd ~/projetos/manjaro-toolbox
python3 app.py
```

Depois abra no navegador:

```text
http://127.0.0.1:8787
```

## Segurança

O app não executa comandos livres digitados pelo usuário. Ele só roda scripts existentes na pasta `scripts/`, ações cadastradas em `actions.json` e pacotes de uma lista permitida no `app.py`, separando pacotes oficiais (`pacman`) de pacotes AUR (`yay`).

Na instalação selecionada, a senha sudo é enviada somente para o processo atual via `sudo -S` e não é salva. Ações rápidas que usam scripts ainda podem pedir senha no terminal onde o app está rodando.

## Ações Disponíveis

- Verificar sistema e espaço em disco
- Listar pacotes órfãos
- Remover pacotes órfãos
- Limpar cache do Pacman com `paccache`
- Limpar cache do Yay/AUR
- Instalar ferramentas essenciais de terminal
- Instalar ferramentas extras de produtividade
- Instalar VLC
- Instalar apps de design e gravação
- Instalar ferramentas de API

## Pacotes Que Já Removemos

- `teamspeak3`
- `eggsmaker`
- `penguins-eggs`
- `collision`
- `gnome-maps`
- `gnome-weather`
- `gnome-tour`
- `gnome-chess`
- `quadrapassel`
- `iagno`
- `decibels`
- `showtime`

## Pacotes Mantidos Com Observação

- `addwater`: mantido porque é dependência de `gnome-layout-switcher`; foi movido para a pasta "Não usamos" no menu.
- `tlauncher`: mantido a pedido.

## Comandos Base

Limpeza segura do cache do Pacman:

```bash
sudo pacman -S pacman-contrib
sudo paccache -rk2
sudo paccache -ruk0
```

Ver órfãos:

```bash
pacman -Qdtq
```

Remover órfãos:

```bash
sudo pacman -Rns $(pacman -Qdtq)
```

Instalar kit recomendado:

```bash
sudo pacman -S vlc btop ripgrep bat eza fzf fd dust duf tldr jq yq httpie pacman-contrib reflector
```

## Estrutura

```text
manjaro-toolbox/
  app.py
  actions.json
  public/
    index.html
    styles.css
    app.js
  scripts/
    *.sh
```
