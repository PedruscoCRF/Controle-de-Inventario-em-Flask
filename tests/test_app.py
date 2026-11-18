import io
import sqlite3

import pytest
from openpyxl import load_workbook

from app import create_app

DADOS = {
    "patrimonio": "PAT-001",
    "nome": "Notebook Dell",
    "serial_number": "SN-ABC123",
    "andar": "2",
    "id_item": "ITEM-01",
    "alocacao": "Secretaria",
}


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "chave-de-teste",
            "DATABASE": str(tmp_path / "teste.db"),
            "MIGRATE_LEGACY_DB": False,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def cadastrar(client, **alteracoes):
    dados = dict(DADOS)
    dados.update(alteracoes)
    return client.post("/cadastro", data=dados, follow_redirects=True)


def id_por_nome(app, nome):
    with sqlite3.connect(app.config["DATABASE"]) as conexao:
        linha = conexao.execute(
            "SELECT id FROM inventario WHERE nome = ?", (nome,)
        ).fetchone()
    return linha[0]


def test_home_abre(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Controle de Inventário" in resposta.get_data(as_text=True)


def test_cadastro_salva_e_mostra_na_consulta(client):
    resposta = cadastrar(client)
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "cadastrado com sucesso" in texto
    assert "Notebook Dell" in texto
    assert "PAT-001" in texto


def test_cadastro_exige_campos_obrigatorios(client):
    resposta = client.post(
        "/cadastro",
        data={**DADOS, "nome": "   "},
    )
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 400
    assert "Preencha os campos obrigatórios" in texto
    assert "Nome" in texto
    # O que já foi digitado continua no formulário
    assert 'value="PAT-001"' in texto


def test_busca_encontra_por_campos_diferentes(client):
    cadastrar(client)
    cadastrar(
        client,
        patrimonio="PAT-002",
        nome="Projetor Epson",
        serial_number="SN-XYZ",
        alocacao="Salão",
    )

    for termo, esperado in [
        ("notebook", "Notebook Dell"),
        ("SN-XYZ", "Projetor Epson"),
        ("Salão", "Projetor Epson"),
        ("PAT-001", "Notebook Dell"),
    ]:
        texto = client.get(f"/consulta?criterio={termo}").get_data(as_text=True)
        assert esperado in texto

    texto = client.get("/consulta?criterio=inexistente").get_data(as_text=True)
    assert "Nenhum item encontrado" in texto


def test_busca_nao_mostra_item_removido(app, client):
    cadastrar(client)
    item_id = id_por_nome(app, "Notebook Dell")

    resposta = client.post(f"/remover/{item_id}", follow_redirects=True)
    assert "removido do inventário" in resposta.get_data(as_text=True)

    texto = client.get("/consulta?criterio=Notebook").get_data(as_text=True)
    assert "Notebook Dell" not in texto
    assert "Nenhum item encontrado" in texto

    with sqlite3.connect(app.config["DATABASE"]) as conexao:
        oculto = conexao.execute(
            "SELECT oculto FROM inventario WHERE id = ?", (item_id,)
        ).fetchone()[0]
    assert oculto == 1


def test_remover_item_inexistente_avisa(app, client):
    resposta = client.post("/remover/999", follow_redirects=True)
    texto = resposta.get_data(as_text=True)
    assert "não encontrado ou já removido" in texto


def test_exportacao_excel_tem_cabecalho_e_itens_ativos(app, client):
    cadastrar(client)
    cadastrar(
        client,
        patrimonio="PAT-002",
        nome="Projetor Epson",
        serial_number="SN-XYZ",
        alocacao="Salão",
    )
    cadastrar(
        client,
        patrimonio="PAT-003",
        nome="Item removido",
        serial_number="SN-REM",
    )
    removido_id = id_por_nome(app, "Item removido")
    client.post(f"/remover/{removido_id}")

    resposta = client.get("/exportar_excel")
    assert resposta.status_code == 200
    assert resposta.mimetype == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    planilha = load_workbook(io.BytesIO(resposta.data)).active
    cabecalho = [celula.value for celula in planilha[1]]
    nomes = [linha[1] for linha in planilha.iter_rows(min_row=2, values_only=True)]

    assert cabecalho == [
        "Patrimônio",
        "Nome",
        "Serial Number",
        "Andar",
        "ID do item",
        "Alocação",
    ]
    assert "Notebook Dell" in nomes
    assert "Projetor Epson" in nomes
    assert "Item removido" not in nomes


def test_exportacao_vazia_funciona(client):
    resposta = client.get("/exportar_excel")
    assert resposta.status_code == 200

    planilha = load_workbook(io.BytesIO(resposta.data)).active
    assert planilha.max_row == 1
    assert planilha["A1"].value == "Patrimônio"


def test_filtros_por_andar_e_alocacao(client):
    cadastrar(client)
    cadastrar(
        client,
        patrimonio="PAT-002",
        nome="Projetor Epson",
        serial_number="SN-XYZ",
        andar="1",
        alocacao="Salão",
    )

    texto = client.get("/consulta?andar=1").get_data(as_text=True)
    assert "Projetor Epson" in texto
    assert "Notebook Dell" not in texto

    texto = client.get("/consulta?alocacao=Secretaria").get_data(as_text=True)
    assert "Notebook Dell" in texto
    assert "Projetor Epson" not in texto


def test_editar_item_atualiza_os_dados(app, client):
    cadastrar(client)
    item_id = id_por_nome(app, "Notebook Dell")

    pagina = client.get(f"/editar/{item_id}").get_data(as_text=True)
    assert "Notebook Dell" in pagina
    assert "SN-ABC123" in pagina

    resposta = client.post(
        f"/editar/{item_id}",
        data={
            **DADOS,
            "nome": "Notebook Dell Latitude",
            "andar": "3",
            "alocacao": "Tesouraria",
        },
        follow_redirects=True,
    )
    texto = resposta.get_data(as_text=True)

    assert "atualizado com sucesso" in texto
    assert "Notebook Dell Latitude" in texto
    assert "Tesouraria" in texto

    with sqlite3.connect(app.config["DATABASE"]) as conexao:
        linha = conexao.execute(
            "SELECT nome, andar, alocacao FROM inventario WHERE id = ?", (item_id,)
        ).fetchone()
    assert linha == ("Notebook Dell Latitude", "3", "Tesouraria")


def test_editar_exige_campos_obrigatorios(app, client):
    cadastrar(client)
    item_id = id_por_nome(app, "Notebook Dell")

    resposta = client.post(
        f"/editar/{item_id}",
        data={**DADOS, "nome": ""},
    )
    texto = resposta.get_data(as_text=True)

    assert resposta.status_code == 400
    assert "Preencha os campos obrigatórios" in texto
    assert "Nome" in texto


def test_restaurar_item_removido(app, client):
    cadastrar(client)
    item_id = id_por_nome(app, "Notebook Dell")
    client.post(f"/remover/{item_id}")

    texto = client.get("/consulta?status=removidos").get_data(as_text=True)
    assert "Notebook Dell" in texto
    assert "Restaurar" in texto

    resposta = client.post(f"/restaurar/{item_id}", follow_redirects=True)
    assert "restaurado no inventário" in resposta.get_data(as_text=True)

    texto = client.get("/consulta").get_data(as_text=True)
    assert "Notebook Dell" in texto

    with sqlite3.connect(app.config["DATABASE"]) as conexao:
        oculto = conexao.execute(
            "SELECT oculto FROM inventario WHERE id = ?", (item_id,)
        ).fetchone()[0]
    assert oculto == 0


def test_lista_de_removidos_nao_mostra_ativos(client):
    cadastrar(client)
    texto = client.get("/consulta?status=removidos").get_data(as_text=True)
    assert "Nenhum item removido" in texto
    assert "Notebook Dell" not in texto


def test_paginacao_mostra_dez_por_pagina(client):
    for numero in range(1, 13):
        cadastrar(
            client,
            patrimonio=f"PAT-{numero:03d}",
            nome=f"Item {numero:02d}",
            serial_number=f"SN-{numero:03d}",
            id_item=f"ITEM-{numero:03d}",
        )

    primeira = client.get("/consulta").get_data(as_text=True)
    assert "Mostrando 1–10 de 12 item(ns)" in primeira
    assert "Página 1 de 2" in primeira

    segunda = client.get("/consulta?pagina=2").get_data(as_text=True)
    assert "Mostrando 11–12 de 12 item(ns)" in segunda
    assert "Página 2 de 2" in segunda

    excedente = client.get("/consulta?pagina=99", follow_redirects=True)
    assert "Página 2 de 2" in excedente.get_data(as_text=True)


def test_ordenacao_decrescente_por_nome(client):
    cadastrar(client, nome="Alpha")
    cadastrar(client, patrimonio="PAT-002", nome="Zulu", serial_number="SN-2")

    texto = client.get("/consulta?ordem=nome&direcao=desc").get_data(as_text=True)
    assert texto.index("Zulu") < texto.index("Alpha")
