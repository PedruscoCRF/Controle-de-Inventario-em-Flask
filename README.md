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
- **Filtrar** por andar e alocação e escolher a ordenação (coluna e direção).
- **Navegar** pelos resultados com 10 itens por página, em tabela no computador
  e em cartões no celular.
- **Editar** um item já cadastrado, corrigindo qualquer um dos campos.
- **Exportar** os itens ativos para `inventario.xlsx`.
- **Remover** um item da consulta e da exportação (exclusão lógica: o registro
  continua no banco, marcado como oculto).
- **Restaurar** um item removido, pela aba **Removidos** ou pela tela de edição.

## Estrutura

```text
app.py                  aplicação e rotas
templates/
  base.html             layout, menu, mensagens e rodapé
  home.html             página inicial
  login.html            tela de acesso
  erro.html             aviso de sessão expirada
  cadastro.html         formulário de cadastro
  editar.html           formulário de edição e ações de remover/restaurar
  consulta.html         busca, filtros, tabela/cartões e paginação
  _form_item.html       campos compartilhados por cadastro e edição
static/
  css/app.css           identidade visual e ajustes de acessibilidade
tests/
  test_app.py           testes do fluxo principal
instance/               banco e chave local (não vão para o Git)
requirements.txt        dependências de execução
requirements-dev.txt    dependências de teste
Procfile                comando de produção (gunicorn)
```

## Rotas

| Rota | O que faz |
|---|---|
| `GET /login` | Tela de acesso |
| `POST /sair` | Encerra a sessão |
| `GET /` | Página inicial com os totais |
| `GET/POST /cadastro` | Cadastra um item |
| `GET /consulta` | Lista os itens com busca, filtros e paginação |
| `GET/POST /editar/<id>` | Edita um item |
| `POST /remover/<id>` | Remove (oculta) um item |
| `POST /restaurar/<id>` | Restaura um item removido |
| `GET /exportar_excel` | Baixa os itens ativos em `.xlsx` |

A consulta aceita os parâmetros `criterio`, `status` (`ativos` ou `removidos`),
`andar`, `alocacao`, `ordem`, `direcao` (`asc`/`desc`) e `pagina`.

## Acesso

O sistema é protegido por uma senha única, compartilhada pela equipe.

- Em produção, defina `INVENTARIO_SENHA` (variável de ambiente).
- Sem essa variável, o app gera uma senha aleatória na primeira execução e a
  grava em `instance/senha` (arquivo fora do Git). Altere o arquivo para trocar
  a senha e reinicie o app.
- Depois de 5 tentativas erradas seguidas, o acesso fica bloqueado por 60
  segundos.
- Todas as telas e a exportação exigem login; o botão **Sair** encerra a sessão.
- Os formulários usam token CSRF e a sessão expira após 12 horas.

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
| `INVENTARIO_SENHA` | Senha de acesso ao sistema | gerada em `instance/senha` |
| `FLASK_SECRET_KEY` | Assina o cookie de sessão | gerada em `instance/secret_key` |
| `INVENTARIO_DB` | Caminho alternativo do banco | `instance/inventario.db` |
| `INVENTARIO_COOKIE_SECURE` | `1` envia o cookie só por HTTPS | desligado |
| `FLASK_DEBUG` | `1` liga o modo de desenvolvimento | desligado |
| `PORT` | Porta do servidor local | `5000` |

Em produção, defina `INVENTARIO_SENHA` e `FLASK_SECRET_KEY` com valores longos e
aleatórios, use HTTPS com `INVENTARIO_COOKIE_SECURE=1` e não use
`FLASK_DEBUG=1`. Trocar `FLASK_SECRET_KEY` encerra todas as sessões abertas.

## Testes

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

Os testes usam um banco temporário e não alteram o inventário real.

## Publicação

Antes de publicar:

1. Defina `INVENTARIO_SENHA` e `FLASK_SECRET_KEY` no painel do serviço.
2. Use HTTPS e ligue `INVENTARIO_COOKIE_SECURE=1`.
3. Confirme que `FLASK_DEBUG` está desligado.
4. Garanta um disco persistente para a pasta `instance/`.

O `Procfile` já traz `web: gunicorn app:app`. **Atenção:** em serviços com
disco efêmero (Heroku, por exemplo), o SQLite é apagado a cada deploy ou
reinício. Para uso publicado, o ideal é migrar para PostgreSQL ou usar um
disco persistente.
