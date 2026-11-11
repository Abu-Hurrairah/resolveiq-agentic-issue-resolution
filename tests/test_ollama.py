"""Run in local CI without installing Ollama: simulate its actual HTTP API."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from fastapi.testclient import TestClient
from app import app
from agent import model_config

class MockOllama(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/api/tags':
            self.send_error(404)
            return
        self.send_json({'models': [{'name': 'qwen2.5:3b', 'model': 'qwen2.5:3b'}]})

    def do_POST(self):
        if self.path != '/api/chat':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        request = json.loads(self.rfile.read(length))
        assert request['model'] == 'qwen2.5:3b'
        assert request['format'] == 'json'
        content = json.dumps({'category': 'Access', 'priority': 'Low',
                              'summary': 'The reported users cannot sign in.',
                              'rationale': 'Authentication problem in the provided report.',
                              'suspected_cause': 'Unconfirmed login redirect.',
                              'recommended_actions': ['Review authentication logs', 'Test sign-in in a staging account'],
                              'draft_reply': 'We have logged your access issue and will investigate.'})
        self.send_json({'message': {'role': 'assistant', 'content': content}, 'done': True})

    def send_json(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_automatic_real_model_inference_and_fallback(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), MockOllama)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setenv('OLLAMA_URL', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.delenv('LLM_MODE', raising=False)
    monkeypatch.delenv('LLM_ENABLED', raising=False)
    try:
        with TestClient(app) as client:
            engine = client.get('/api/engine').json()
            assert engine['available'] and engine['mode'] == 'ollama', engine
            response = client.post('/api/issues', json={'title': 'Login redirect for multiple users',
                'description': 'Several users cannot access the portal due to a redirect loop after login.',
                'reporter': 'Support QA'})
            assert response.status_code == 201, response.text
            issue = response.json()
            assert issue['source'] == 'Ollama · qwen2.5:3b', issue
            assert issue['analysis']['model_used'] == 'qwen2.5:3b'
            assert issue['analysis']['summary'] == 'The reported users cannot sign in.'
            assert issue['priority'] == 'High'  # model's Low is not allowed to downgrade risk
            assert issue['status'] == 'Needs review'
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
    # No Ollama server: the same app must keep working automatically.
    assert model_config(force=True)['available'] is False
    with TestClient(app) as client:
        response = client.post('/api/issues', json={'title': 'Invoice payment duplicated',
            'description': 'The customer was billed twice for the same invoice after checkout.',
            'reporter': 'Finance QA'})
        assert response.status_code == 201
        issue = response.json()
        assert issue['source'] == 'Offline rules · fallback'
        assert issue['analysis']['model_used'] is None
        assert len(issue['analysis']['recommended_actions']) >= 2


def test_manual_off_mode_disables_ai(monkeypatch):
    monkeypatch.setenv('LLM_MODE', 'off')
    assert model_config(force=True)['available'] is False
    assert 'disabled' in model_config()['reason'].lower()
