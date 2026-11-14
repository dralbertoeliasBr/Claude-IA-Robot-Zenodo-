#!/usr/bin/env python3
# Teste do Robô Zenodo com um Zenodo FALSO local. Não usa a internet. Nada vai ao Zenodo.
# Rodar: python3 teste_robo.py
import json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
ROBO = os.path.join(AQUI, "robo_zenodo.py")
chamadas = []


class Falso(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _resp(self, dados, codigo=200):
        corpo = json.dumps(dados).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _ler(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_POST(self):
        self._ler()
        chamadas.append(("POST", self.path, self.headers.get("Authorization")))
        porta = self.server.server_address[1]
        if self.path == "/api/deposit/depositions":
            return self._resp({"id": 123, "links": {"bucket": "http://127.0.0.1:%d/api/files/balde" % porta}}, 201)
        if self.path == "/api/deposit/depositions/123/actions/newversion":
            return self._resp({"id": 123, "links": {"latest_draft": "http://x/api/deposit/depositions/456"}}, 201)
        if self.path == "/api/deposit/depositions/123/actions/publish":
            return self._resp({"id": 123, "doi": "10.5072/zenodo.123"}, 202)
        self._resp({"erro": "rota"}, 404)

    def do_PUT(self):
        corpo = self._ler()
        chamadas.append(("PUT", self.path, len(corpo)))
        if self.path == "/api/deposit/depositions/123":
            md = json.loads(corpo)["metadata"]
            assert md["license"] == "cc-by-4.0", md
            return self._resp({"id": 123, "links": {"html": "http://falso/deposit/123"}})
        return self._resp({"key": self.path.rsplit("/", 1)[-1]}, 201)

    def do_GET(self):
        chamadas.append(("GET", self.path))
        porta = self.server.server_address[1]
        if self.path == "/api/deposit/depositions/123":
            return self._resp({"id": 123, "state": "done", "submitted": True, "doi": "10.5072/zenodo.123",
                               "metadata": {"title": "Teste", "version": "1", "license": {"id": "cc-by-4.0"},
                                            "creators": [{"name": "Elias"}]},
                               "files": [{"filename": "a.txt", "filesize": 3,
                                          "links": {"download": "http://127.0.0.1:%d/api/files/balde/a.txt" % porta}}],
                               "links": {"html": "http://falso/deposit/123"}})
        if self.path == "/api/files/balde/a.txt":
            self.send_response(200); self.send_header("Content-Length", "3"); self.end_headers()
            return self.wfile.write(b"abc")
        if self.path.startswith("/api/deposit/depositions?"):
            return self._resp([{"id": 123, "state": "done", "doi": "10.5072/zenodo.123",
                                "metadata": {"title": "Teste", "license": {"id": "cc-by-4.0"}}}])
        self._resp({}, 404)


def rodar(args, extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("ZENODO") and k != "OK_DO_SOUNAVY"}
    env.update(extra)
    r = subprocess.run([sys.executable, ROBO] + args, cwd=AQUI, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def checar(nome, cond, saida=""):
    print(("OK   " if cond else "FALHOU ") + nome)
    if not cond:
        print(saida)
        sys.exit(1)


def main():
    srv = HTTPServer(("127.0.0.1", 0), Falso)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    api = "http://127.0.0.1:%d/api" % srv.server_address[1]
    base = {"ZENODO_PASTA": "exemplo", "ZENODO_API": api, "ZENODO_TOKEN": "falso-de-teste"}

    c, s = rodar(["ensaio"], {"ZENODO_PASTA": "exemplo"})
    checar("ensaio mostra modo SANDBOX e não envia", c == 0 and "Modo: SANDBOX (treino)" in s and "ENSAIO: nada enviado." in s, s)

    c, s = rodar(["rascunho"], {"ZENODO_PASTA": "exemplo"})
    checar("sem token: para com erro claro", c != 0 and "ZENODO_TOKEN não configurado" in s, s)

    c, s = rodar(["rascunho"], {"ZENODO_PASTA": "pasta-que-nao-existe", "ZENODO_TOKEN": "x"})
    checar("sem metadados: para com erro claro", c != 0 and "falta" in s, s)

    c, s = rodar(["rascunho"], base)
    checar("rascunho cria depósito, sobe 1 arquivo e NÃO publica",
           c == 0 and "id 123" in s and "Nada publicado" in s
           and not any(x[1].endswith("/publish") for x in chamadas), s)
    checar("token vai no cabeçalho, nunca na URL",
           any(x[0] == "POST" and x[2] == "Bearer falso-de-teste" for x in chamadas)
           and not any("falso-de-teste" in x[1] for x in chamadas), str(chamadas))

    c, s = rodar(["publicar", "123"], base)
    checar("publicar sem OK do Sounavy: BLOQUEADO", c != 0 and "BLOQUEADO" in s, s)

    c, s = rodar(["publicar", "123"], dict(base, OK_DO_SOUNAVY="sim"))
    checar("publicar com OK: devolve DOI", c == 0 and "10.5072/zenodo.123" in s, s)

    c, s = rodar(["listar"], base)
    checar("listar mostra licença", c == 0 and "licença: cc-by-4.0" in s, s)

    c, s = rodar(["ver", "123"], base)
    checar("ver mostra detalhes", c == 0 and "Versão: 1 | Licença: cc-by-4.0" in s and "a.txt" in s, s)

    import tempfile, shutil
    tmp = tempfile.mkdtemp()
    shutil.copy(ROBO, tmp)
    env = dict(base); env.pop("ZENODO_PASTA")
    r = subprocess.run([sys.executable, os.path.join(tmp, "robo_zenodo.py"), "baixar", "123"], cwd=tmp,
                       env=dict({k: v for k, v in os.environ.items() if not k.startswith("ZENODO")}, **env),
                       capture_output=True, text=True)
    baixado = os.path.join(tmp, "exportado", "123", "a.txt")
    checar("baixar exporta metadados e arquivo",
           r.returncode == 0 and os.path.exists(os.path.join(tmp, "exportado", "123", "deposito.json"))
           and open(baixado, "rb").read() == b"abc", r.stdout + r.stderr)
    shutil.rmtree(tmp)

    c, s = rodar(["nova-versao", "123"], base)
    checar("nova-versao abre rascunho 456 e não publica", c == 0 and "id 456" in s and "Nada publicado" in s, s)

    c, s = rodar(["ver", "abc"], base)
    checar("id inválido: para com erro", c != 0 and "inválido" in s, s)

    print("TODOS OS TESTES PASSARAM (Zenodo falso, local).")


if __name__ == "__main__":
    main()
