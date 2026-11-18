"""Controle de Inventário — aplicação Flask.

Rodar localmente:
    python app.py

O banco fica em ``instance/inventario.db``. Na primeira execução, se existir
um ``inventario.db`` antigo na raiz do projeto, ele é copiado para lá.
"""

from __future__ import annotations

import io
import os
import secrets
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
from flask import (
    Flask,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parent
LEGACY_DB = BASE_DIR / "inventario.db"

# Campos do formulário: (nome no banco, rótulo exibido)
CAMPOS = (
    ("patrimonio", "Patrimônio"),
    ("nome", "Nome"),
    ("serial_number", "Serial Number"),
    ("andar", "Andar"),
    ("id_item", "ID do item"),
    ("alocacao", "Alocação"),
)

COLUNAS_EXPORT = {
    "patrimonio": "Patrimônio",
    "nome": "Nome",
    "serial_number": "Serial Number",
    "andar": "Andar",
    "id_item": "ID do item",
    "alocacao": "Alocação",
}

CATEGORIAS_ALERTA = {"success", "danger", "warning", "info"}


def _local_secret_key(app: Flask) -> str:
    """Lê a chave de sessão do ambiente ou de um arquivo local ignorado pelo Git."""
    chave = os.environ.get("FLASK_SECRET_KEY")
    if chave:
        return chave

    arquivo = Path(app.instance_path) / "secret_key"
    if arquivo.exists():
        return arquivo.read_text(encoding="utf-8").strip()

    chave = secrets.token_hex(32)
    arquivo.write_text(chave, encoding="utf-8")
    return chave


def _preparar_banco(app: Flask) -> None:
    """Cria a pasta e a tabela; migra o banco antigo na primeira execução."""
    caminho = Path(app.config["DATABASE"])
    caminho.parent.mkdir(parents=True, exist_ok=True)

    if (
        app.config.get("MIGRATE_LEGACY_DB", True)
        and not caminho.exists()
        and LEGACY_DB.exists()
    ):
        shutil.copy2(LEGACY_DB, caminho)

    conexao = sqlite3.connect(caminho)
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio TEXT NOT NULL,
            nome TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            andar TEXT NOT NULL,
            id_item TEXT NOT NULL,
            alocacao TEXT NOT NULL,
            oculto BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_inventario_nome ON inventario(nome)"
    )
    conexao.commit()
    conexao.close()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        DATABASE=os.environ.get("INVENTARIO_DB")
        or str(Path(app.instance_path) / "inventario.db"),
        MIGRATE_LEGACY_DB=True,
        SECRET_KEY=None,
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    app.config["DATABASE"] = str(Path(app.config["DATABASE"]).expanduser().resolve())
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = _local_secret_key(app)

    _preparar_banco(app)

    # ------------------------------------------------------------------
    # Banco de dados
    # ------------------------------------------------------------------
    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(current_app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def fechar_db(_excecao: BaseException | None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def variaveis_globais() -> dict:
        return {"current_year": date.today().year}

    # ------------------------------------------------------------------
    # Rotas
    # ------------------------------------------------------------------
    @app.get("/")
    def index():
        db = get_db()
        total = db.execute(
            "SELECT COUNT(*) FROM inventario WHERE oculto = 0"
        ).fetchone()[0]
        ocultos = db.execute(
            "SELECT COUNT(*) FROM inventario WHERE oculto = 1"
        ).fetchone()[0]
        return render_template("home.html", total=total, ocultos=ocultos)

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        form = {nome: "" for nome, _ in CAMPOS}

        if request.method == "POST":
            form = {
                nome: request.form.get(nome, "").strip() for nome, _ in CAMPOS
            }
            faltando = [rotulo for nome, rotulo in CAMPOS if not form[nome]]

            if faltando:
                flash(
                    "Preencha os campos obrigatórios: " + ", ".join(faltando) + ".",
                    "danger",
                )
                return render_template("cadastro.html", form=form, campos=CAMPOS), 400

            db = get_db()
            db.execute(
                """
                INSERT INTO inventario
                    (patrimonio, nome, serial_number, andar, id_item, alocacao)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                tuple(form[nome] for nome, _ in CAMPOS),
            )
            db.commit()

            flash(f'Item "{form["nome"]}" cadastrado com sucesso!', "success")
            return redirect(url_for("consulta"))

        return render_template("cadastro.html", form=form, campos=CAMPOS)

    @app.get("/consulta")
    def consulta():
        criterio = request.args.get("criterio", "").strip()
        db = get_db()

        if criterio:
            like = f"%{criterio}%"
            inventario = db.execute(
                """
                SELECT * FROM inventario
                WHERE oculto = 0 AND (
                    patrimonio LIKE ? OR nome LIKE ? OR serial_number LIKE ?
                    OR andar LIKE ? OR id_item LIKE ? OR alocacao LIKE ?
                )
                ORDER BY nome COLLATE NOCASE
                """,
                (like,) * 6,
            ).fetchall()
        else:
            inventario = db.execute(
                """
                SELECT * FROM inventario
                WHERE oculto = 0
                ORDER BY nome COLLATE NOCASE
                """
            ).fetchall()

        return render_template(
            "consulta.html", inventario=inventario, criterio=criterio
        )

    @app.get("/exportar_excel")
    def exportar_excel():
        db = get_db()
        registros = db.execute(
            """
            SELECT patrimonio, nome, serial_number, andar, id_item, alocacao
            FROM inventario
            WHERE oculto = 0
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()

        df = pd.DataFrame(
            [dict(registro) for registro in registros],
            columns=list(COLUNAS_EXPORT),
        ).rename(columns=COLUNAS_EXPORT)

        saida = io.BytesIO()
        with pd.ExcelWriter(saida, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Inventário")
            planilha = writer.sheets["Inventário"]
            for indice, coluna in enumerate(df.columns, start=1):
                largura = max(
                    [len(str(coluna))] + [len(str(valor)) for valor in df[coluna]]
                )
                planilha.column_dimensions[get_column_letter(indice)].width = min(
                    largura + 2, 45
                )

        saida.seek(0)
        return send_file(
            saida,
            as_attachment=True,
            download_name="inventario.xlsx",
            mimetype=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        )

    @app.post("/remover/<int:id>")
    def remover(id: int):
        db = get_db()
        item = db.execute(
            "SELECT nome FROM inventario WHERE id = ? AND oculto = 0", (id,)
        ).fetchone()

        if item is None:
            flash("Item não encontrado ou já removido.", "warning")
        else:
            db.execute("UPDATE inventario SET oculto = 1 WHERE id = ?", (id,))
            db.commit()
            flash(f'Item "{item["nome"]}" removido do inventário.', "success")

        return redirect(url_for("consulta"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
