from flask import Flask, request, jsonify, render_template, send_file
import sqlite3
import csv
import io

app = Flask(__name__)
DB_PATH = "municipios.db"

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

# Endpoint para executar consulta
@app.route("/executar", methods=["POST"])
def executar():
    data = request.json
    tabela = data.get("tabela")
    colunas = data.get("colunas", "*")
    filtros = data.get("filtros", [])
    limite = data.get("limite", 10)  # Limite padrão de 10 registros

    # Construir a cláusula WHERE com segurança
    clausulas = []
    valores = []
    for filtro in filtros:
        operador_logico = filtro.get("operador_logico", "AND").upper()  # Padrão: AND
        coluna = filtro.get("coluna")
        operador = filtro.get("operador")
        valor = filtro.get("valor")

        if coluna and operador:
            # Adicionar operador lógico entre filtros
            if clausulas:
                clausulas.append(operador_logico)

            # Adicionar filtro com parâmetros para evitar SQL Injection
            clausulas.append(f"{coluna} {operador} ?")
            valores.append(valor)

    where_clause = " ".join(clausulas)
    sql_query = f"SELECT {', '.join(colunas)} FROM {tabela}"
    if where_clause:
        sql_query += f" WHERE {where_clause}"
    sql_query += f" LIMIT {limite}"

    try:
        conn = get_db_connection()
        cursor = conn.execute(sql_query, valores)
        resultados = cursor.fetchall()
        colunas_resultado = [desc[0] for desc in cursor.description]
        conn.close()

        return jsonify({
            "sql": sql_query,
            "colunas": colunas_resultado,
            "resultados": [dict(row) for row in resultados]
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

# Endpoint para exportar todos os resultados
@app.route("/exportar", methods=["POST"])
def exportar():
    data = request.json
    tabela = data.get("tabela")
    colunas = data.get("colunas", "*")
    filtros = data.get("filtros", [])

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

    try:
        conn = get_db_connection()
        resultados = conn.execute(sql_query).fetchall()
        colunas_resultado = [desc[0] for desc in conn.execute(sql_query).description]
        conn.close()

        # Criar CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=colunas_resultado)
        writer.writeheader()
        writer.writerows([dict(row) for row in resultados])
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="resultados.csv"
        )
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)

