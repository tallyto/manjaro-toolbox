#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import subprocess
import urllib.parse

ROOT = Path(__file__).resolve().parent
ACTIONS_FILE = ROOT / 'actions.json'
PUBLIC = ROOT / 'public'
HOST = '127.0.0.1'
PORT = 8787

PACKAGE_GROUPS = [
    {
        'id': 'terminal',
        'title': 'Terminal essencial',
        'packages': [
            {'name': 'btop', 'description': 'Monitor de sistema no terminal'},
            {'name': 'ripgrep', 'description': 'Busca texto em arquivos com rg'},
            {'name': 'bat', 'description': 'cat com syntax highlight'},
            {'name': 'eza', 'description': 'ls moderno'},
            {'name': 'fzf', 'description': 'Busca interativa'},
            {'name': 'fd', 'description': 'find mais simples'},
            {'name': 'dust', 'description': 'Uso de disco por pasta'},
            {'name': 'duf', 'description': 'Visão de discos e partições'},
            {'name': 'tldr', 'description': 'Exemplos rápidos de comandos'},
        ],
    },
    {
        'id': 'dev',
        'title': 'Desenvolvimento e API',
        'packages': [
            {'name': 'jq', 'description': 'Manipular JSON'},
            {'name': 'yq', 'description': 'Manipular YAML'},
            {'name': 'httpie', 'description': 'Cliente HTTP amigável'},
            {'name': 'insomnia', 'description': 'Cliente gráfico para APIs'},
            {'name': 'lazygit', 'description': 'Interface terminal para Git'},
            {'name': 'delta', 'description': 'Diff bonito para Git'},
            {'name': 'lazydocker', 'description': 'Interface terminal para Docker'},
        ],
    },
    {
        'id': 'system',
        'title': 'Sistema e manutenção',
        'packages': [
            {'name': 'pacman-contrib', 'description': 'Ferramentas como paccache'},
            {'name': 'reflector', 'description': 'Atualizar mirrors'},
            {'name': 'nmap', 'description': 'Diagnóstico de rede'},
            {'name': 'traceroute', 'description': 'Rota até hosts'},
            {'name': 'whois', 'description': 'Consulta de domínios/IPs'},
            {'name': 'restic', 'description': 'Backups criptografados'},
            {'name': 'rclone', 'description': 'Sincronização com nuvem'},
        ],
    },
    {
        'id': 'desktop',
        'title': 'Desktop e produtividade',
        'packages': [
            {'name': 'vlc', 'description': 'Reprodutor de áudio e vídeo'},
            {'name': 'keepassxc', 'description': 'Gerenciador de senhas local'},
            {'name': 'gimp', 'description': 'Editor de imagens'},
            {'name': 'inkscape', 'description': 'Editor vetorial'},
            {'name': 'obs-studio', 'description': 'Gravação e live'},
            {'name': 'zoxide', 'description': 'cd inteligente'},
            {'name': 'starship', 'description': 'Prompt moderno'},
        ],
    },
]

ALLOWED_PACKAGES = {
    package['name']
    for group in PACKAGE_GROUPS
    for package in group['packages']
}


def load_actions():
    with ACTIONS_FILE.open(encoding='utf-8') as fh:
        return json.load(fh)


def find_action(action_id):
    for action in load_actions():
        if action['id'] == action_id:
            return action
    return None


def sudo_command(command, password):
    if password:
        return ['sudo', '-S', '-p', '', *command], password + '\n'
    return ['sudo', *command], None


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        body = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/', '/index.html'):
            body = (PUBLIC / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return
        self.send_error(404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/actions':
            self._send_json(200, {'actions': load_actions()})
            return
        if parsed.path == '/api/packages':
            self._send_json(200, {'groups': PACKAGE_GROUPS})
            return
        if parsed.path in ('/', '/index.html'):
            self._send_file(PUBLIC / 'index.html')
            return
        requested = (PUBLIC / parsed.path.lstrip('/')).resolve()
        if PUBLIC in requested.parents:
            self._send_file(requested)
            return
        self.send_error(403)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/run':
            self._run_action()
            return
        if parsed.path == '/api/install-selected':
            self._install_selected()
            return
        self.send_error(404)

    def _payload(self):
        length = int(self.headers.get('Content-Length', '0'))
        return json.loads(self.rfile.read(length) or b'{}')

    def _run_action(self):
        payload = self._payload()
        action = find_action(payload.get('id'))
        if not action:
            self._send_json(404, {'ok': False, 'error': 'Ação não encontrada.'})
            return

        script = (ROOT / action['script']).resolve()
        if ROOT not in script.parents or not script.exists():
            self._send_json(400, {'ok': False, 'error': 'Script inválido.'})
            return

        try:
            proc = subprocess.run(
                ['bash', str(script)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                timeout=60 * 30,
            )
            output = (proc.stdout or '') + (proc.stderr or '')
            self._send_json(200, {
                'ok': proc.returncode == 0,
                'code': proc.returncode,
                'output': output.strip() or '(sem saída)'
            })
        except subprocess.TimeoutExpired:
            self._send_json(408, {'ok': False, 'error': 'Tempo limite excedido.'})

    def _install_selected(self):
        payload = self._payload()
        requested = payload.get('packages') or []
        password = payload.get('password') or ''

        if not isinstance(requested, list):
            self._send_json(400, {'ok': False, 'error': 'Lista de pacotes inválida.'})
            return

        packages = []
        for package in requested:
            if package not in ALLOWED_PACKAGES:
                self._send_json(400, {'ok': False, 'error': f'Pacote não permitido: {package}'})
                return
            if package not in packages:
                packages.append(package)

        if not packages:
            self._send_json(400, {'ok': False, 'error': 'Selecione pelo menos um pacote.'})
            return

        command, stdin = sudo_command(['pacman', '-S', '--needed', '--noconfirm', *packages], password)
        try:
            proc = subprocess.run(
                command,
                input=stdin,
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                timeout=60 * 45,
            )
            output = (proc.stdout or '') + (proc.stderr or '')
            self._send_json(200, {
                'ok': proc.returncode == 0,
                'code': proc.returncode,
                'output': output.strip() or '(sem saída)'
            })
        except subprocess.TimeoutExpired:
            self._send_json(408, {'ok': False, 'error': 'Tempo limite excedido.'})


def main():
    print(f'Manjaro Toolbox rodando em http://{HOST}:{PORT}', flush=True)
    print('Use Ctrl+C para parar.', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
