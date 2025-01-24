import pandas as pd
import sqlite3
from itertools import combinations
from fuzzywuzzy import process

# Conectar ao banco SQLite
DB_PATH = "municipios.db"
conn = sqlite3.connect(DB_PATH)

# Carregar os dados para inspecionar valores únicos
data = pd.read_sql("SELECT * FROM municipios", conn)

# Gerar SQL dinâmico para todos os valores únicos de cada coluna
# Inclui instruções para listar e contabilizar os dados com múltiplos filtros
def gerar_sql_por_colunas_com_multiplos_filtros(data):
    """
    Gera perguntas e SQL para filtros combinados com até o número total de colunas da tabela.
    """
    perguntas_sql = []
    colunas = data.columns
    max_criterios = len(colunas)  # Máximo de critérios igual ao número de colunas

    # Gerar combinações de colunas para múltiplos filtros
    for num_criterios in range(1, max_criterios + 1):  # Começa com 1 critério até o máximo
        for colunas_combinadas in combinations(colunas, num_criterios):
            # Para cada combinação de colunas, gerar valores únicos
            valores_combinados = [data[coluna].dropna().unique() for coluna in colunas_combinadas]

            # Gerar todas as combinações de valores únicos
            for valores in zip(*valores_combinados):
                # Construir o filtro SQL dinâmico
                filtro_sql = " AND ".join([f"{coluna} = '{valor}'" for coluna, valor in zip(colunas_combinadas, valores)])

                # Adicionar pergunta e SQL ao conjunto
                perguntas_sql.append({
                    "pergunta": f"Quais são os dados para {filtro_sql}?",
                    "sql": f"SELECT * FROM municipios WHERE {filtro_sql};"
                })

                # Adicionar uma pergunta para contagem
                perguntas_sql.append({
                    "pergunta": f"Quantos registros existem para {filtro_sql}?",
                    "sql": f"SELECT COUNT(*) FROM municipios WHERE {filtro_sql};"
                })

    return perguntas_sql

# Gerar perguntas e SQLs
PERGUNTAS_SQL = gerar_sql_por_colunas_com_multiplos_filtros(data)

# Confirmar com o usuário antes de executar
def confirmar_consulta(pergunta_usuario):
    """
    Busca a pergunta mais similar e pede confirmação ao usuário antes de executar.
    """
    perguntas = [p["pergunta"] for p in PERGUNTAS_SQL]
    pergunta_mais_similar, similaridade = process.extractOne(pergunta_usuario, perguntas)

    if similaridade > 70:  # Limite de similaridade
        pergunta_sql = next(p for p in PERGUNTAS_SQL if p["pergunta"] == pergunta_mais_similar)

        print(f"\nPergunta encontrada: {pergunta_mais_similar} (Similaridade: {similaridade}%)")
        confirmacao = input("Você deseja executar essa consulta? (s/n): ").strip().lower()
        if confirmacao == "s":
            return pergunta_sql
        else:
            print("Consulta cancelada pelo usuário.")
            return None
    else:
        print("Desculpe, não encontrei uma pergunta correspondente.")
        return None

# Executar SQL no banco de dados
def executar_sql(sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    resultado = cursor.fetchall()
    return resultado, [desc[0] for desc in cursor.description]

# Exibir instruções gerais de consulta
def exibir_instrucoes():
    print("\nInstruções gerais de consulta:")
    print("- Pergunte usando palavras-chave relevantes, como 'dados', 'quantos', ou 'onde'.")
    print("- Exemplo 1: 'Quais são os dados para mun_uf = SP?'")
    print("- Exemplo 2: 'Quantos registros existem para mun_regiao = Nordeste?'")
    print("- Exemplo 3: 'Quais são os dados para mun_uf = SP e mun_populacao > 10000 e regiao = 1?'")
    print("- O sistema buscará a consulta mais similar e solicitará confirmação antes de executar.\n")

# Interface Interativa
print("Bem-vindo ao sistema de consulta dinâmico!")
exibir_instrucoes()
print("Digite sua pergunta (ou 'sair' para encerrar):")

while True:
    pergunta_usuario = input("> ")
    if pergunta_usuario.lower() == "sair":
        print("Encerrando o programa. Até mais!")
        break

    # Confirmar e executar a consulta
    pergunta_sql = confirmar_consulta(pergunta_usuario)
    if pergunta_sql:
        try:
            resultado, colunas = executar_sql(pergunta_sql["sql"])

            # Exibir os resultados em formato tabular
            if resultado:
                df = pd.DataFrame(resultado, columns=colunas)
                print("\nResultado da consulta:")
                print(df.to_string(index=False))
            else:
                print("\nNenhum resultado encontrado.")
        except Exception as e:
            print("\nErro ao executar a consulta:", e)

# Fechar conexão
conn.close()

