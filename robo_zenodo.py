#!/usr/bin/env python3
# Robô Zenodo v1 — conceito: Sounavy | engenharia: Claude (12/11/2026)
# Tudo num arquivo só. Sem bibliotecas externas.
#
# Comandos:
#   ensaio            confere metadados e arquivos. Não usa a internet. Nada é enviado.
#   rascunho          cria um depósito em RASCUNHO e sobe os arquivos. Não publica.
#   publicar <id>     publica um rascunho. Só roda com OK_DO_SOUNAVY=sim.
#   listar            lista seus depósitos (título, estado, licença, DOI). Só leitura.
#   ver <id>          mostra os detalhes de um depósito. Só leitura.
#   baixar <id>       exporta metadados + arquivos de um depósito para exportado/<id>/. Só leitura.
#   nova-versao <id>  abre um RASCUNHO de nova versão de um registro publicado. Não publica.
#
# Modo: SANDBOX (treino) por padrão. Só usa o Zenodo real com ZENODO_MODO=real.
# Token: vem da variável de ambiente ZENODO_TOKEN (Secret do GitHub). Nunca escrito em arquivo.
import json, os, sys, urllib.request, urllib.error

SANDBOX = "https://sandbox.zenodo.org/api"
REAL = "https://zenodo.org/api"
CAMPOS = ["title", "upload_type", "description", "creators"]
LICENCA_PADRAO = "cc-by-4.0"


def pasta():
    return os.environ.get("ZENODO_PASTA", "publicar")


def modo_real():
    return os.environ.get("ZENODO_MODO") == "real"


def base():
    # ZENODO_API serve só para testes locais (servidor falso).
    return os.environ.get("ZENODO_API") or (REAL if modo_real() else SANDBOX)


def nome_modo():
    return "REAL (zenodo.org)" if modo_real() else "SANDBOX (treino)"


def token():
    t = os.environ.get("ZENODO_TOKEN", "").strip()
    if not t:
        sys.exit("ERRO: ZENODO_TOKEN não configurado")
    return t


def pedir(metodo, url, dados=None, corpo=None, tipo="application/json"):
    if dados is not None:
        corpo = json.dumps(dados).encode()
    req = urllib.request.Request(url, data=corpo, method=metodo)
    req.add_header("Authorization", "Bearer " + token())
    req.add_header("Accept", "application/json")
    if corpo is not None:
        req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            t = r.read().decode() or "{}"
            return json.loads(t)
    except urllib.error.HTTPError as e:
        sys.exit("ERRO Zenodo %s: %s" % (e.code, e.read().decode()[:500]))
    except urllib.error.URLError as e:
        sys.exit("ERRO de rede: %s" % e.reason)


def ler_metadados():
    caminho = os.path.join(pasta(), "metadados.json")
    if not os.path.exists(caminho):
        sys.exit("ERRO: falta %s" % caminho)
    with open(caminho, encoding="utf-8") as f:
        m = json.load(f)
    falta = [c for c in CAMPOS if not m.get(c)]
    if falta:
        sys.exit("ERRO: faltam campos em metadados.json: " + ", ".join(falta))
    m.setdefault("license", LICENCA_PADRAO)
    return m


def arquivos():
    p = pasta()
    lista = [f for f in sorted(os.listdir(p))
             if f != "metadados.json" and not f.startswith(".")
             and os.path.isfile(os.path.join(p, f))]
    if not lista:
        sys.exit("ERRO: nenhum arquivo para enviar em %s/" % p)
    return lista


def saida_github(chave, valor):
    # Passa o id do rascunho para o próximo passo do GitHub Actions.
    destino = os.environ.get("GITHUB_OUTPUT")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write("%s=%s\n" % (chave, valor))


def resumo_github(texto):
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def cmd_ensaio():
    print("Modo: " + nome_modo())
    print("Pasta: %s/" % pasta())
    m = ler_metadados()
    print("Título: " + m["title"])
    print("Tipo: " + m["upload_type"])
    print("Licença: " + m["license"])
    print("Autores: " + "; ".join(c.get("name", "?") for c in m["creators"]))
    for f in arquivos():
        print("Arquivo: %s (%d bytes)" % (f, os.path.getsize(os.path.join(pasta(), f))))
    print("ENSAIO: nada enviado.")


def cmd_rascunho():
    print("Modo: " + nome_modo())
    m = ler_metadados()
    lista = arquivos()
    d = pedir("POST", base() + "/deposit/depositions", dados={})
    dep_id, balde = d["id"], d["links"]["bucket"]
    print("Rascunho criado: id %s" % dep_id)
    for f in lista:
        with open(os.path.join(pasta(), f), "rb") as fh:
            pedir("PUT", "%s/%s" % (balde, f), corpo=fh.read(), tipo="application/octet-stream")
        print("Enviado: " + f)
    d = pedir("PUT", "%s/deposit/depositions/%s" % (base(), dep_id), dados={"metadata": m})
    link = d.get("links", {}).get("html", "")
    print("Link para revisar: " + link)
    print("RASCUNHO PRONTO. Nada publicado. Para publicar: OK do Sounavy.")
    saida_github("deposito_id", dep_id)
    resumo_github("### Rascunho Zenodo pronto\n- Modo: %s\n- id: `%s`\n- Revisar: %s\n- Nada publicado."
                  % (nome_modo(), dep_id, link))


def cmd_publicar(dep_id):
    if os.environ.get("OK_DO_SOUNAVY") != "sim":
        sys.exit("BLOQUEADO: falta o OK do Sounavy (OK_DO_SOUNAVY=sim).")
    if not str(dep_id).isdigit():
        sys.exit("ERRO: id do rascunho inválido: %r" % dep_id)
    print("Modo: " + nome_modo())
    d = pedir("POST", "%s/deposit/depositions/%s/actions/publish" % (base(), dep_id))
    doi = d.get("doi") or d.get("metadata", {}).get("doi", "")
    print("PUBLICADO: id %s | DOI %s" % (dep_id, doi))
    resumo_github("### Publicado no Zenodo\n- Modo: %s\n- id: `%s`\n- DOI: %s" % (nome_modo(), dep_id, doi))


def cmd_listar():
    print("Modo: " + nome_modo())
    pagina = 1
    while True:
        lote = pedir("GET", "%s/deposit/depositions?size=100&page=%d" % (base(), pagina))
        if not lote:
            break
        for d in lote:
            md = d.get("metadata", {})
            lic = md.get("license", "")
            if isinstance(lic, dict):
                lic = lic.get("id", "")
            print("%s | %s | %s | licença: %s | DOI: %s" % (
                d.get("id"), d.get("state", "?"), md.get("title", "")[:80],
                lic or "?", d.get("doi", "") or "-"))
        if len(lote) < 100:
            break
        pagina += 1


def ver_deposito(dep_id):
    if not str(dep_id).isdigit():
        sys.exit("ERRO: id inválido: %r" % dep_id)
    return pedir("GET", "%s/deposit/depositions/%s" % (base(), dep_id))


def cmd_ver(dep_id):
    print("Modo: " + nome_modo())
    d = ver_deposito(dep_id)
    md = d.get("metadata", {})
    lic = md.get("license", "")
    if isinstance(lic, dict):
        lic = lic.get("id", "")
    print("id: %s | estado: %s | publicado: %s" % (d.get("id"), d.get("state"), d.get("submitted")))
    print("Título: " + md.get("title", ""))
    print("Versão: %s | Licença: %s" % (md.get("version", "-"), lic or "?"))
    print("Autores: " + "; ".join(c.get("name", "?") for c in md.get("creators", [])))
    print("DOI: " + (d.get("doi") or md.get("prereserve_doi", {}).get("doi", "-") + " (reservado)"))
    for f in d.get("files", []):
        print("Arquivo: %s (%s bytes)" % (f.get("filename"), f.get("filesize")))
    print("Link: " + d.get("links", {}).get("html", ""))


def cmd_baixar(dep_id):
    print("Modo: " + nome_modo())
    d = ver_deposito(dep_id)
    destino = os.path.join("exportado", str(dep_id))
    os.makedirs(destino, exist_ok=True)
    with open(os.path.join(destino, "deposito.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("Salvo: %s/deposito.json" % destino)
    for f in d.get("files", []):
        nome = os.path.basename(f.get("filename", ""))
        url = f.get("links", {}).get("download")
        if not nome or not url:
            continue
        req = urllib.request.Request(url)
        req.add_header("Authorization", "Bearer " + token())
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(os.path.join(destino, nome), "wb") as out:
                out.write(r.read())
        except urllib.error.HTTPError as e:
            sys.exit("ERRO ao baixar %s: %s" % (nome, e.code))
        print("Baixado: %s/%s" % (destino, nome))
    print("EXPORTAÇÃO PRONTA. Nada foi alterado no Zenodo.")


def cmd_nova_versao(dep_id):
    print("Modo: " + nome_modo())
    d = ver_deposito(dep_id)
    if not d.get("submitted"):
        sys.exit("ERRO: o %s ainda é rascunho; edite-o direto, não precisa de nova versão." % dep_id)
    r = pedir("POST", "%s/deposit/depositions/%s/actions/newversion" % (base(), dep_id))
    novo = r.get("links", {}).get("latest_draft", "").rstrip("/").rsplit("/", 1)[-1]
    print("Rascunho de NOVA VERSÃO criado: id %s" % novo)
    print("Os arquivos antigos foram copiados para o rascunho. Nada publicado.")
    saida_github("deposito_id", novo)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__ or "Uso: robo_zenodo.py ensaio|rascunho|publicar <id>|listar")
    c = sys.argv[1]
    if c == "ensaio":
        cmd_ensaio()
    elif c == "rascunho":
        cmd_rascunho()
    elif c == "publicar":
        if len(sys.argv) < 3:
            sys.exit("ERRO: diga o id do rascunho: robo_zenodo.py publicar <id>")
        cmd_publicar(sys.argv[2])
    elif c == "listar":
        cmd_listar()
    elif c in ("ver", "baixar", "nova-versao"):
        if len(sys.argv) < 3:
            sys.exit("ERRO: diga o id: robo_zenodo.py %s <id>" % c)
        {"ver": cmd_ver, "baixar": cmd_baixar, "nova-versao": cmd_nova_versao}[c](sys.argv[2])
    else:
        sys.exit("Comando desconhecido: %s (use ensaio, rascunho, publicar, listar, ver, baixar ou nova-versao)" % c)


if __name__ == "__main__":
    main()
