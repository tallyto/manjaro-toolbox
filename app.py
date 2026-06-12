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


def load_actions():
    with ACTIONS_FILE.open(encoding='utf-8') as fh:
        return json.load(fh)


def find_action(action_id):
    for action in load_actions():
        if action['id'] == action_id:
            return action
    return None


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

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/actions':
            self._send_json(200, {'actions': load_actions()})
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
        if parsed.path != '/api/run':
            self.send_error(404)
            return

        length = int(self.headers.get('Content-Length', '0'))
        payload = json.loads(self.rfile.read(length) or b'{}')
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


def main():
    print(f'Manjaro Toolbox rodando em http://{HOST}:{PORT}')
    print('Use Ctrl+C para parar.')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
