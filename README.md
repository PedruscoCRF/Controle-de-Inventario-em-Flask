# Controle de Inventário em Flask

Sistema simples para cadastrar, consultar e exportar os itens do inventário.
Feito com Flask, SQLite e Bootstrap, sem etapa de build.

## Como rodar

Requisitos: Python 3.10 ou mais recente.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>.

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## O que dá para fazer

- **Cadastrar** um item com patrimônio, nome, serial, andar, ID e alocação.
- **Consultar** por qualquer um desses campos, com busca parcial.
- **Exportar** os itens ativos para `inventario.xlsx`.
- **Remover** um item da consulta e da exportação (exclusão lógica: o registro
  continua no banco, marcado como oculto).

## Estrutura

```text
app.py                  aplicação e rotas
templates/
  base.html             layout, menu, mensagens e rodapé
  home.html             página inicial
  cadastro.html         formulário de cadastro
  consulta.html         busca, tabela e exportação
tests/
  test_app.py           testes do fluxo principal
instance/               banco e chave local (não vão para o Git)
requirements.txt        dependências de execução
requirements-dev.txt    dependências de teste
Procfile                comando de produção (gunicorn)
```

## Banco de dados

- O banco fica em `instance/inventario.db` e **não é versionado**.
- Na primeira execução, se existir um `inventario.db` antigo na raiz do
  projeto, ele é copiado automaticamente para `instance/`.
- Para fazer backup, pare a aplicação e copie o arquivo
  `instance/inventario.db`.
- Para começar do zero, apague `instance/inventario.db` e rode o app novamente.

## Configurações

| Variável | Para que serve | Padrão |
|---|---|---|
| `FLASK_SECRET_KEY` | Assina o cookie de sessão | gerada em `instance/secret_key` |
| `INVENTARIO_DB` | Caminho alternativo do banco | `instance/inventario.db` |
| `FLASK_DEBUG` | `1` liga o modo de desenvolvimento | desligado |
| `PORT` | Porta do servidor local | `5000` |

Em produção, defina `FLASK_SECRET_KEY` com um valor longo e aleatório e não
use `FLASK_DEBUG=1`.

## Testes

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Os testes usam um banco temporário e não alteram o inventário real.

## Publicação

O `Procfile` já traz `web: gunicorn app:app`. **Atenção:** em serviços com
disco efêmero (Heroku, por exemplo), o SQLite é apagado a cada deploy ou
reinício. Para uso publicado, o ideal é migrar para PostgreSQL ou usar um
disco persistente.
