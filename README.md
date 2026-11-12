# Claude-IA-Robot-Zenodo-
Robot 

# Robô Zenodo v1

Conceito: **Sounavy** (Antônio Alberto Lopes Elias, ORCID 0000-0002-5602-9916).
Engenharia: **Claude** (12/11/2026).

## O que já existe (honestidade de autoria)
- O próprio Zenodo tem integração oficial com o GitHub: cada *release* de um repositório público vira um registro com DOI.
- Este robô faz outra coisa: publica **qualquer arquivo** (PDF, textos, código) com **duas etapas** e o **OK do Sounavy** no meio.

## Como funciona
| Etapa | O que faz | Publica? |
|---|---|---|
| `ensaio` | confere metadados e arquivos, sem internet | não |
| `rascunho` | cria o depósito e sobe os arquivos | não |
| `publicar <id>` | publica o rascunho revisado; exige `OK_DO_SOUNAVY=sim` | sim |
| `listar` | lista seus depósitos com licença e DOI | não (só leitura) |

- Modo padrão: **SANDBOX (treino)**. O real só com `ZENODO_MODO=real`.
- Licença padrão: **CC BY 4.0** (`cc-by-4.0`), se o `metadados.json` não disser outra.
- O token fica só no cofre do GitHub (Secrets). Nunca em arquivo.

## Pelo iPhone (app do GitHub)
1. Ponha os arquivos e o `metadados.json` na pasta `publicar/` (modelo em `exemplo/`).
2. Actions > **Robô Zenodo** > Run workflow > etapa `rascunho`, modo `sandbox`.
3. Abra o link do rascunho, revise.
4. Run workflow de novo > etapa `publicar` + o id do rascunho. Este passo usa o environment `ok-do-sounavy`.

## Segredos necessários (Settings > Secrets and variables > Actions)
- `ZENODO_SANDBOX_TOKEN` — token de https://sandbox.zenodo.org (treino)
- `ZENODO_TOKEN` — token de https://zenodo.org (real)

## Testes
`python3 teste_robo.py` — roda o robô contra um Zenodo **falso** local. Nada vai à internet.
