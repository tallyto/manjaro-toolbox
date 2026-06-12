#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import shutil
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
            {'name': 'postman-bin', 'description': 'Cliente gráfico para APIs (AUR)', 'source': 'aur'},
            {'name': 'insomnia-bin', 'description': 'Cliente gráfico para APIs (AUR)', 'source': 'aur'},
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
    package['name']: package.get('source', 'pacman')
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


def sudo_input(password):
    if not password:
        return None
    # sudo may ask again after one failed read; provide enough lines without storing it.
    return (password + '\n') * 3


def sudo_command(command, password):
    if password:
        return ['sudo', '-S', '-p', '', *command], sudo_input(password)
    return ['sudo', *command], None


def run_sudo(command, password, timeout):
    full_command, stdin = sudo_command(command, password)
    return subprocess.run(
        full_command,
        input=stdin,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


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
        if parsed.path == '/api/uninstall-selected':
            self._uninstall_selected()
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


    def _selected_packages(self, requested):
        if not isinstance(requested, list):
            return None, 'Lista de pacotes inválida.'

        packages = []
        for package in requested:
            if package not in ALLOWED_PACKAGES:
                return None, f'Pacote não permitido: {package}'
            if package not in packages:
                packages.append(package)
        if not packages:
            return None, 'Selecione pelo menos um pacote.'
        return packages, None

    def _validate_sudo(self, password):
        if not password:
            return None
        validate = run_sudo(['-v'], password, 30)
        if validate.returncode != 0:
            output = (validate.stdout or '') + (validate.stderr or '')
            return {
                'ok': False,
                'code': validate.returncode,
                'output': 'Falha ao validar sudo. Verifique a senha digitada.\n\n' + (output.strip() or '(sem saída)')
            }
        return None

    def _uninstall_selected(self):
        payload = self._payload()
        packages, error = self._selected_packages(payload.get('packages') or [])
        password = payload.get('password') or ''

        if error:
            self._send_json(400, {'ok': False, 'error': error})
            return

        try:
            sudo_error = self._validate_sudo(password)
            if sudo_error:
                self._send_json(200, sudo_error)
                return

            # AUR packages are also registered in pacman's local database after installation,
            # so removal should use pacman too. Calling yay here can require an interactive TTY.
            proc = run_sudo(['pacman', '-Rns', '--noconfirm', *packages], password, 60 * 30)
            output = (proc.stdout or '') + (proc.stderr or '')
            self._send_json(200, {
                'ok': proc.returncode == 0,
                'code': proc.returncode,
                'output': ('== Remoção de pacotes ==\n' + output.strip()) if output.strip() else '(sem saída)'
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

        try:
            if password:
                validate = run_sudo(['-v'], password, 30)
                if validate.returncode != 0:
                    output = (validate.stdout or '') + (validate.stderr or '')
                    self._send_json(200, {
                        'ok': False,
                        'code': validate.returncode,
                        'output': 'Falha ao validar sudo. Verifique a senha digitada.\n\n' + (output.strip() or '(sem saída)')
                    })
                    return

            pacman_packages = [package for package in packages if ALLOWED_PACKAGES[package] == 'pacman']
            aur_packages = [package for package in packages if ALLOWED_PACKAGES[package] == 'aur']
            outputs = []
            ok = True
            code = 0

            if pacman_packages:
                proc = run_sudo(['pacman', '-S', '--needed', '--noconfirm', *pacman_packages], password, 60 * 45)
                outputs.append('== Pacotes oficiais ==\n' + ((proc.stdout or '') + (proc.stderr or '')).strip())
                ok = ok and proc.returncode == 0
                code = proc.returncode if proc.returncode != 0 else code
                if proc.returncode != 0:
                    self._send_json(200, {
                        'ok': False,
                        'code': proc.returncode,
                        'output': '\n\n'.join(part for part in outputs if part).strip() or '(sem saída)'
                    })
                    return

            if aur_packages:
                if not shutil.which('yay'):
                    self._send_json(200, {
                        'ok': False,
                        'code': 127,
                        'output': 'yay não está instalado. Não foi possível instalar pacotes AUR: ' + ' '.join(aur_packages)
                    })
                    return
                proc = subprocess.run(
                    ['yay', '-S', '--needed', '--noconfirm', *aur_packages],
                    input=sudo_input(password),
                    cwd=str(ROOT),
                    text=True,
                    capture_output=True,
                    timeout=60 * 60,
                )
                outputs.append('== Pacotes AUR ==\n' + ((proc.stdout or '') + (proc.stderr or '')).strip())
                ok = ok and proc.returncode == 0
                code = proc.returncode if proc.returncode != 0 else code

            self._send_json(200, {
                'ok': ok,
                'code': code,
                'output': '\n\n'.join(part for part in outputs if part).strip() or '(sem saída)'
            })
        except subprocess.TimeoutExpired:
            self._send_json(408, {'ok': False, 'error': 'Tempo limite excedido.'})


def main():
    print(f'Manjaro Toolbox rodando em http://{HOST}:{PORT}', flush=True)
    print('Use Ctrl+C para parar.', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
