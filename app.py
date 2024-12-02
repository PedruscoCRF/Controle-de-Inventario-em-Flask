import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import io

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Função para conectar ao banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('inventario.db')
    conn.row_factory = sqlite3.Row  # Permite acessar os resultados como dicionários
    return conn

# Função para criar a tabela se não existir
def init_db():
    conn = get_db_connection()
    conn.execute('''
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
    ''')
    conn.commit()
    conn.close()

# Iniciar o banco de dados
init_db()

# Página inicial (Home)
@app.route('/')
def index():
    return render_template('home.html')

# Página de Cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        patrimonio = request.form['patrimonio']
        nome = request.form['nome']
        serial_number = request.form['serial_number']
        andar = request.form['andar']
        id_item = request.form['id_item']
        alocacao = request.form['alocacao']

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO inventario (patrimonio, nome, serial_number, andar, id_item, alocacao)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (patrimonio, nome, serial_number, andar, id_item, alocacao))
        conn.commit()
        conn.close()

        flash('Item cadastrado com sucesso!', 'success')
        return redirect(url_for('cadastro'))

    return render_template('cadastro.html')

# Página de Consulta
@app.route('/consulta', methods=['GET', 'POST'])
def consulta():
    if request.method == 'POST':
        criterio = request.form['criterio']
        conn = get_db_connection()
        query = '''
            SELECT * FROM inventario WHERE patrimonio LIKE ? OR nome LIKE ?
        '''
        inventario = conn.execute(query, ('%' + criterio + '%', '%' + criterio + '%')).fetchall()
        conn.close()
    else:
        conn = get_db_connection()
        inventario = conn.execute('SELECT * FROM inventario WHERE oculto = 0').fetchall()
        conn.close()

    return render_template('consulta.html', inventario=inventario)

# Função para exportar os dados para um arquivo Excel
@app.route('/exportar_excel')
def exportar_excel():
    conn = get_db_connection()
    query = "SELECT * FROM inventario WHERE oculto = 0"
    inventario = conn.execute(query).fetchall()
    conn.close()

    # Convertendo os dados para um DataFrame do pandas
    df = pd.DataFrame(inventario, columns=["id", "patrimonio", "nome", "serial_number", "andar", "id_item", "alocacao", "oculto"])

    # Gerando um arquivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario')

    # Salva o arquivo no formato Excel
    output.seek(0)

    # Retorna o arquivo Excel para o navegador
    return send_file(output, as_attachment=True, download_name="inventario.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Página para remover item
@app.route('/remover/<int:id>', methods=['POST'])
def remover(id):
    conn = get_db_connection()
    conn.execute('UPDATE inventario SET oculto = 1 WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Item removido com sucesso!', 'success')
    return redirect(url_for('consulta'))

if __name__ == '__main__':
    app.run(debug=True)
