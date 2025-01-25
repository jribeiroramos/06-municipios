from flask import Flask, request, jsonify, render_template, send_file
import sqlite3
import csv
import io
import logging

app = Flask(__name__)
DB_PATH = "municipios.db"

# Configuração do logger
logging.basicConfig(
    filename='app.log',  # Nome do arquivo de log
    level=logging.INFO,  # Registrar apenas mensagens importantes
    format='%(asctime)s - %(message)s'  # Formato da mensagem de log
)

# Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Página inicial
@app.route("/")
def index():
    conn = get_db_connection()
    tabelas = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    return render_template("index.html", tabelas=[t["name"] for t in tabelas])

# Endpoint para obter colunas
@app.route("/colunas/<tabela>")
def colunas(tabela):
    conn = get_db_connection()
    colunas = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    conn.close()
    return jsonify([col["name"] for col in colunas])

# Endpoint para executar consulta dinâmica
@app.route("/executar", methods=["POST"])
def executar():
    data = request.json
    tabela = data.get("tabela")
    colunas = data.get("colunas", "*")
    filtros = data.get("filtros", [])
    agrupamento = data.get("agrupamento", [])
    limite = data.get("limite", 10)  # Limite padrão de 10 registros

    # Construir a cláusula WHERE
    clausulas = []
    for filtro in filtros:
        operador_logico = filtro.get("operador_logico", "")
        coluna = filtro.get("coluna")
        operador = filtro.get("operador")
        valor = filtro.get("valor")

        if clausulas and operador_logico:
            clausulas.append(operador_logico)

        clausulas.append(f"{coluna} {operador} '{valor}'")

    where_clause = " ".join(clausulas)
    sql_query = f"SELECT {', '.join(colunas)} FROM {tabela}"
    if where_clause:
        sql_query += f" WHERE {where_clause}"
    if agrupamento:
        sql_query += f" GROUP BY {', '.join(agrupamento)}"
    sql_query += f" LIMIT {limite}"

    try:
        conn = get_db_connection()
        resultados = conn.execute(sql_query).fetchall()
        colunas_resultado = [desc[0] for desc in conn.execute(sql_query).description]
        conn.close()

        return jsonify({
            "sql": sql_query,
            "colunas": colunas_resultado,
            "resultados": [dict(row) for row in resultados]
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

# Endpoint para executar SQL personalizado
@app.route("/executar-sql", methods=["POST"])
def executar_sql_personalizado():
    data = request.json
    sql_query = data.get("sql", "").strip()

    if not sql_query:
        return jsonify({"erro": "Nenhuma consulta SQL fornecida."}), 400

    # Log para depuração
    print(f"SQL Recebido: {sql_query}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_query)
        resultados = cursor.fetchall()
        colunas_resultado = [desc[0] for desc in cursor.description]
        conn.close()

        return jsonify({
            "sql": sql_query,
            "colunas": colunas_resultado,
            "resultados": [dict(zip(colunas_resultado, row)) for row in resultados]
        })
    except Exception as e:
        print(f"Erro ao executar SQL: {e}")  # Log de erro
        return jsonify({"erro": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)

