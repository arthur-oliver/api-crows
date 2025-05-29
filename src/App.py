#--------------------------- Imports ----------------------
import os, uuid, time, shutil
import pandas as pd
import numpy as np
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, session, flash
from gerar_graficos import balanca_comercial,ranking_municipios,funil_por_produto,ranking_municipios_cargas,municipio_cargas  # Função que gera o HTML do gráfico


# ================== CARREGAR DATAFRAMES ANTES DE INICIAR O APP ==================

base_path = os.path.dirname(os.path.abspath(__file__))

# Carrega os CSVs de municípios e SH4
caminho_mun = os.path.join(base_path, 'tabelas-relacionais', 'df_mun.csv')
df_mun = pd.read_csv(caminho_mun) if os.path.exists(caminho_mun) else pd.DataFrame()

caminho_sh4 = os.path.join(base_path, 'tabelas-relacionais', 'df_sh4.csv')
df_sh4 = pd.read_csv(caminho_sh4) if os.path.exists(caminho_sh4) else pd.DataFrame()

caminho_pais = os.path.join(base_path, 'tabelas-relacionais', 'df_pais.csv')
df_pais = pd.read_csv(caminho_pais) if os.path.exists(caminho_pais) else pd.DataFrame()

caminho_regioes = os.path.join(base_path, 'tabelas-relacionais', 'df_regioes.csv')
df_regioes = pd.read_csv(caminho_regioes) if os.path.exists(caminho_regioes) else pd.DataFrame()


# Função para carregar dados por ano
def carregar_dados_dataframe(ano, tipo):
    caminho = os.path.join(base_path, 'arquivos-brutos-csv', 'exportacoes' if tipo == 'exp' else 'importacoes', f'df_{tipo}_{ano}.csv')
    return pd.read_csv(caminho) if os.path.exists(caminho) else pd.DataFrame()

# Carrega dados completos (exp e imp)
df_completo_exp, df_completo_imp = pd.DataFrame(), pd.DataFrame()
for ano in range(2025, 2019 - 1, -1):
    df_completo_exp = pd.concat([df_completo_exp, carregar_dados_dataframe(ano, 'exp')], ignore_index=True)
    df_completo_imp = pd.concat([df_completo_imp, carregar_dados_dataframe(ano, 'imp')], ignore_index=True)

# ================== INICIANDO O FLASK ================================

#----------------- Criação da Aplicação Flask -------------
app = Flask(__name__,
            template_folder=os.path.join(os.getcwd(), 'templates'),
            static_folder=os.path.join(os.getcwd(), 'static'))

# Sessions

load_dotenv()
# método que necessita adicionar a chave manualmente da internet em um arquivo '.env'
app.secret_key = os.getenv('FLASK_SECRET_KEY') 

# tempo para logoff (segundos)
SESSION_TIMEOUT = 60

@app.before_request
def manage_session():
    if request.endpoint == 'graficos':
        # Verifica se a sessão tem um timestamp de início
        session_timestamp = session.get('timestamp')
        
        if session_timestamp:
            # Verifica o tempo passado desde o timestamp
            elapsed_time = time.time() - session_timestamp
            
            if elapsed_time > SESSION_TIMEOUT:
                session_id = session.pop('session_id', None)
                if session_id:
                    try:
                        shutil.rmtree(f'graficos-dinamicos/{session_id}/')
                        # print(f"Pasta graficos-dinamicos/{session_id}/ e seu conteúdo excluídos com sucesso.")
                    except OSError as e:
                        print(f'Erro ao excluir arquivos: {e}')
                # print("Sessão expirada e apagada!")

        # Cria session caso não exista uma
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['timestamp'] = time.time()
            # print(session['session_id'])


#---------------------- Página Inicial --------------------
@app.route('/')
def home():
    return render_template('home.html')

#---------------------- Página Feedback --------------------
@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

# Variavel Global
caminhos = []

#---------------------- Página Gráficos --------------------
@app.route('/graficos', methods=['GET', 'POST'])
def graficos():
    mostrar_grafico = False
    grafico_quinto = False

    #Limpa os caminhos antes de gerar novos gráficos
    global caminhos
    caminhos.clear()
    tipo =''
    metrica = ''
    metrica_lower =''

#------------ Se o usuário enviou o formulário--------------
    if request.method == 'POST':

        # Recupera os índices (0 a 74)
        index_inicial = int(request.form['data_inicial'])
        index_final = int(request.form['data_final'])

        # Cria a lista de meses possíveis
        meses = pd.date_range(start='2019-01', end='2025-03', freq='MS').strftime('%Y-%m').tolist()       

        # Converte os índices para datas reais
        data_inicial = meses[index_inicial]
        data_final = meses[index_final]

        # Converte para int se quiser usar como ano
        ano_inicial = int(data_inicial[:4])
        ano_final = int(data_final[:4])

        periodo_inicial_grafico = meses[index_inicial]
        periodo_final_grafico= meses[index_final]

        #pegando o filtro do front
        tipo = request.form.get('exp-imp','')
        metrica = request.form.get('metrica','')
        filtro = request.form.get('filtro','')
        opcao = request.form.get('opcao','')
        

        #verifica se foi escolhido o tipo e a metrica
        if tipo and metrica and filtro:
            data_inicial = f'{data_inicial}-01'
            data_final = f'{data_final}-01'

            # Filtrar os dados com base no intervalo de datas
            df_filtrado_exp, df_filtrado_imp = pd.DataFrame(), pd.DataFrame()
            df_filtrado_exp = df_completo_exp[(df_completo_exp['DATA'] >= data_inicial) & (df_completo_exp['DATA'] <= data_final)]
            df_filtrado_imp = df_completo_imp[(df_completo_imp['DATA'] >= data_inicial) & (df_completo_imp['DATA'] <= data_final)]

            carga,cidade,regiao = '','',''
            if filtro == 'municipios':
                pass  # não faz nada e segue o código normalmente

            elif filtro == 'microrregiao':

                # A variável 'regiao' recebe a opção de região desejada
                regiao = opcao

                # Filtra o DataFrame 'df_regioes' para encontrar os municípios que pertencem à região selecionada
                cidades_regiao = df_regioes[df_regioes['Região'] == regiao]['Município']

                # Filtra o DataFrame 'df_mun' para encontrar os códigos dos municípios ('CO_MUN') que pertencem à região selecionada
                cods_mun = df_mun[df_mun['NO_MUN_MIN'].isin(cidades_regiao)][['NO_MUN_MIN','CO_MUN']]

                # Filtra 'df_filtrado_exp' para manter apenas os registros com 'CO_MUN' (código do município) presentes na lista 'cods_mun'
                df_filtrado_exp = df_filtrado_exp[df_filtrado_exp['CO_MUN'].isin(cods_mun['CO_MUN'])]

                if df_filtrado_exp.empty:
                    flash("A região possui um ou mais valores nulos ou inexistentes para as métricas selecionadas.")
                    pass

                # Reseta os índices do DataFrame 'df_filtrado_exp' após o filtro, removendo qualquer índice antigo
                df_filtrado_exp.reset_index(drop=True, inplace=True)

                # Repete o processo para 'df_filtrado_imp', filtrando os registros de 'df_filtrado_imp' que correspondem aos municípios da região selecionada
                df_filtrado_imp = df_filtrado_imp[df_filtrado_imp['CO_MUN'].isin(cods_mun['CO_MUN'])]

                # Reseta os índices do DataFrame 'df_filtrado_imp' após o filtro, para manter um índice contínuo e limpo
                df_filtrado_imp.reset_index(drop=True, inplace=True)

            elif filtro == 'portes':
                try:
                    cidade = opcao.split(" - ")[0]
                    cidade = int(cidade)
                    
                    # Calcular o valor FOB total (exportações e importações)
                    df_exp = df_filtrado_exp.groupby('CO_MUN')['VL_FOB'].sum().reset_index(name='EXPORTACAO')
                    df_imp = df_filtrado_imp.groupby('CO_MUN')['VL_FOB'].sum().reset_index(name='IMPORTACAO')
                    
                    # Junta os dataframes de exportação e importação
                    df_balanca = pd.merge(df_exp, df_imp, on='CO_MUN', how='outer').fillna(0)

                    # Adiciona a coluna de "Força Comercial" (diferente entre exportações e importações)
                    df_balanca['FORCA_COMERCIAL'] = df_balanca['EXPORTACAO'] - df_balanca['IMPORTACAO']

                    # Ordena os municípios pela "força comercial"
                    df_balanca = df_balanca.sort_values(by='FORCA_COMERCIAL', ascending=False).reset_index(drop=True)
                    
                    # Encontrar a posição do município desejado na lista
                    posicao = df_balanca[df_balanca['CO_MUN'] == cidade].index[0]

                    # Calcula os limites iniciais
                    start = max(posicao - 5, 0)
                    end = start + 10

                    # Se passar do final, ajusta o start de novo para compensar
                    if end > len(df_balanca):
                        end = len(df_balanca)
                        start = max(end - 10, 0)

                    # Seleciona os códigos dos municípios vizinhos
                    cods_vizinhos = df_balanca.iloc[start:end]['CO_MUN']

                    # Filtra os dataframes de exportação e importação para esses municípios vizinhos
                    df_filtrado_exp = df_filtrado_exp[df_filtrado_exp['CO_MUN'].isin(cods_vizinhos)].reset_index(drop=True)
                    df_filtrado_imp = df_filtrado_imp[df_filtrado_imp['CO_MUN'].isin(cods_vizinhos)].reset_index(drop=True)

                    grafico_quinto = True

                except (Exception, TypeError, ValueError, np._core._exceptions._UFuncNoLoopError) as e:
                    flash(f"Um ou mais valores são nulos ou inexistentes, impedindo a geração dos gráficos. Erro: {e}")
                    return render_template('graficos.html')

            elif filtro == 'carga':
                carga = opcao.split(" - ")[0]
                carga = int(carga)

                df_exp_carga = df_filtrado_exp[df_filtrado_exp['SH4'] == carga]
                df_imp_carga  = df_filtrado_imp[df_filtrado_imp['SH4'] == carga]

                if (df_exp_carga.empty or df_imp_carga.empty):
                    flash("A carga possui valor nulo ou não existente para um ou mais municípios.")
                    pass 

                df_exp_agrupado = df_exp_carga.groupby('CO_MUN')['VL_FOB'].sum().reset_index()
                df_imp_agrupado = df_imp_carga.groupby('CO_MUN')['VL_FOB'].sum().reset_index()

                df_exp_agrupado = df_exp_agrupado.sort_values(by='VL_FOB', ascending=False)
                df_imp_agrupado = df_imp_agrupado.sort_values(by='VL_FOB', ascending=False)

                cods_exp_carga = df_exp_agrupado['CO_MUN']
                cods_imp_carga = df_imp_agrupado['CO_MUN']

                df_filtrado_exp = df_filtrado_exp[df_filtrado_exp['CO_MUN'].isin(cods_exp_carga)]
                df_filtrado_exp.reset_index(drop=True, inplace=True)

                df_filtrado_imp = df_filtrado_imp[df_filtrado_imp['CO_MUN'].isin(cods_imp_carga)]
                df_filtrado_imp.reset_index(drop=True, inplace=True)

            #Se dados existem, gera os gráficos
            if not df_filtrado_exp.empty and not df_filtrado_imp.empty:
                if tipo == 'Exportacões':
                    caminhos = [
                        balanca_comercial(df_filtrado_exp, df_filtrado_imp, df_mun, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        funil_por_produto(df_filtrado_exp, df_sh4, tipo, metrica, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        ranking_municipios(df_mun, df_filtrado_exp, df_filtrado_imp, tipo, metrica, df_sh4, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        ranking_municipios_cargas(df_mun, df_filtrado_exp, df_filtrado_imp, tipo, metrica, df_sh4, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                    ]
                    if cidade:
                        caminhos.append(municipio_cargas(df_filtrado_exp, df_mun, df_sh4, cidade, tipo, metrica, '', session['session_id']))

                elif tipo == 'Importacões':
                    caminhos = [
                        balanca_comercial(df_filtrado_exp, df_filtrado_imp, df_mun, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        funil_por_produto(df_filtrado_imp, df_sh4, tipo, metrica, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        ranking_municipios(df_mun, df_filtrado_exp, df_filtrado_imp, tipo, metrica, df_sh4, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                        ranking_municipios_cargas(df_mun, df_filtrado_exp, df_filtrado_imp, tipo, metrica, df_sh4, '', session['session_id'],periodo_inicial_grafico,periodo_final_grafico),
                    ]
                    if cidade:
                        caminhos.append(municipio_cargas(df_filtrado_imp, df_mun, df_sh4, cidade, tipo, metrica, '', session['session_id']))

                session['caminhos'] = caminhos
                mostrar_grafico = True

    tipo_lower = tipo.lower()
    if tipo_lower == 'exportacões':
        tipo_lower = 'exportações'
    elif tipo_lower == 'importacões':
        tipo_lower = 'importações'
    if metrica == 'VALOR AGREGADO':
        metrica_lower = 'valor agregado'
    elif metrica == 'KG_LIQUIDO':
        metrica_lower = 'valor kg líquido'
    elif metrica == 'VL_FOB':
        metrica_lower = 'valor FOB'

    #Renderiza a página de gráficos
    return render_template('graficos.html', mostrar_grafico=mostrar_grafico, grafico_quinto=grafico_quinto, tipo=tipo_lower, metrica=metrica_lower)

#------ Rotas para exibir os arquivos HTML dos gráficos ----
@app.route('/grafico_primeiro')
def grafico_primeiro():
    caminhos = session.get('caminhos', [])
    if len(caminhos) < 1 or not os.path.exists(caminhos[0]):
        return abort(404, description="Gráfico não encontrado.")
    pasta, nome_arquivo = os.path.split(caminhos[0])
    return send_from_directory(pasta, nome_arquivo)

@app.route('/grafico_segundo')
def grafico_segundo():
    caminhos = session.get('caminhos', [])
    if len(caminhos) < 2 or not os.path.exists(caminhos[1]):
        return abort(404, description="Gráfico não encontrado.")
    pasta, nome_arquivo = os.path.split(caminhos[1])
    return send_from_directory(pasta, nome_arquivo)

@app.route('/grafico_terceiro')
def grafico_terceiro():
    caminhos = session.get('caminhos', [])
    if len(caminhos) < 3 or not os.path.exists(caminhos[2]):
        return abort(404, description="Gráfico não encontrado.")
    pasta, nome_arquivo = os.path.split(caminhos[2])
    return send_from_directory(pasta, nome_arquivo)

@app.route('/grafico_quarto')
def grafico_quarto():
    caminhos = session.get('caminhos', [])
    if len(caminhos) < 4 or not os.path.exists(caminhos[3]):
        return abort(404, description="Gráfico não encontrado.")
    pasta, nome_arquivo = os.path.split(caminhos[3])
    return send_from_directory(pasta, nome_arquivo)

@app.route('/grafico_quinto')
def grafico_quinto():
    caminhos = session.get('caminhos', [])
    if len(caminhos) < 5 or not os.path.exists(caminhos[4]):
        return abort(404, description="Gráfico não encontrado.")
    pasta, nome_arquivo = os.path.split(caminhos[4])
    return send_from_directory(pasta, nome_arquivo)

# ---------------------- Banco de Dados Feedback ----------------------
import mysql.connector

# Configurações de conexão com o MySQL
db_config = {
    'host': os.getenv('bd_host'),
    'user': os.getenv('bd_user'), 
    'password': os.getenv('bd_password'),
    'database': os.getenv('bd_name')
}

# ---------------------- Rota para receber feedback ----------------------
@app.route('/enviar', methods=['POST'])
def enviar_feedback():
    avaliacao = request.form['avaliacao']
    mensagem = request.form['mensagem']

    try:
        # Conectar ao banco de dados
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()

        # Inserção no banco de dados
        cur.execute("INSERT INTO feedback (avaliacao, mensagem) VALUES (%s, %s)", (avaliacao, mensagem))
        conn.commit()

        cur.close()
        conn.close()

        # Se inserção for bem-sucedida, mensagem de sucesso
        status = "Feedback enviado com sucesso! Agradecemos por sua avaliação."

    except Exception as e:
        # Caso ocorra erro, mensagem de erro
        status = f"Erro ao enviar o feedback ao Banco de dado: {str(e)}. Tente novamente."

    # Redireciona para a página de feedback com o status da operação
    return render_template('feedback.html', status=status)

#----------------- Inicia o servidor Flask para Feedback ---------------
#Roda a aplicação localmente com debug=True (útil durante o desenvolvimento).
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)