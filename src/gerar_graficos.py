import os
import pandas as pd
import plotly.express as px


from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ------------------------- Funções --------------------------------------------
# Função adiciona coluna de ano
def adicionar_ano(df):
    df['DATA'] = pd.to_datetime(df['DATA'])
    df['ANO'] = df['DATA'].dt.year
    return df

# Função agrupa por colunas com operação de soma ou média
def agrupar_df(df, colunas, coluna_valor, operacao='sum'):
    if operacao == 'sum':
        return df.groupby(colunas)[coluna_valor].sum().reset_index()
    elif operacao == 'mean':
        return df.groupby(colunas)[coluna_valor].mean().reset_index()

# Função Mescla dois DataFrames
def mesclar_df(df1, df2, colunas, how='left'):
    return pd.merge(df1, df2, on=colunas, how=how)

# Cria uma nova coluna a partir da diferença de outras duas
def calcular_diferenca(df, col1, col2, nova_coluna):
    df[nova_coluna] = df[col1] - df[col2]
    return df

# Seleciona top N cidades com maior valor em uma coluna
def selecionar_top_cidades(df, coluna_valor, n=5):
    top = (
        df.groupby('NO_MUN_MIN')[coluna_valor]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .index
    )
    return df[df['NO_MUN_MIN'].isin(top)]

# Padroniza adição de ano e mês no df
def adicionar_mes_ano(df):
    df['DATA'] = pd.to_datetime(df['DATA'])
    df['ANO'] = df['DATA'].dt.year
    df['MES'] = df['DATA'].dt.month
    df['ANO_MES'] = df['DATA'].dt.to_period('M').astype(str)
    return df

def quebrar_texto(texto, largura=30):
    return '<br>'.join([texto[i:i+largura] for i in range(0, len(texto), largura)])

# ------------------------- Método que faz o Gráfico de Balança Comercial -------------------------------------------
# Função principal da balança comercial
def balanca_comercial(df_exp, df_imp, df_mun, retorno, session_id,periodo_inicial_grafico,periodo_final_grafico):
    df_exp = adicionar_mes_ano(df_exp)
    df_imp = adicionar_mes_ano(df_imp)

    # Verfica o periodo está dentre um ano
    coluna = 'ANO'
    qtd_exp, qtd_imp = df_exp['ANO'].nunique(), df_imp['ANO'].nunique()
    if qtd_exp <= 1 and qtd_imp <= 1:
        coluna = 'MES'
    elif qtd_exp <=3 and qtd_imp <= 3:
        coluna = 'DATA'

    # Agrupamento
    exp_anos = agrupar_df(df_exp, ['CO_MUN', coluna], 'VL_FOB', 'sum')
    exp_anos.rename(columns={'VL_FOB': 'EXPORTACAO'}, inplace=True)

    imp_anos = agrupar_df(df_imp, ['CO_MUN', coluna], 'VL_FOB', 'sum')
    imp_anos.rename(columns={'VL_FOB': 'IMPORTACAO'}, inplace=True)

    # Mescla exportação e importação
    balanca = mesclar_df(exp_anos, imp_anos, ['CO_MUN', coluna], how='outer').fillna(0)

    # Calcula a balança
    balanca = calcular_diferenca(balanca, 'EXPORTACAO', 'IMPORTACAO', 'BALANCA')

    # Adiciona o nome dos municípios
    balanca = mesclar_df(balanca, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])

    # Top cidades
    top_cidades = selecionar_top_cidades(balanca, 'BALANCA', n=10)

    # Paleta
    paleta_de_cores = [
        "#003d80",   # azul bem escuro
        "#0059b3",  # azul escuro
        "#0073e6",  # azul intenso
        "#3399ff",  # azul
        "#66b2ff",  # azul médio
        "#99ccff",  # azul claro
        "#cce5ff"  # azul bem claro  
    ]

    # Gráfico
    fig = px.line(
        top_cidades,
        x=coluna,
        y='BALANCA',
        color='NO_MUN_MIN',
        markers=True,
        title=None,
        labels={'NO_MUN_MIN': 'Município', 'BALANCA': 'Balança Comercial (US$)'},
        line_shape='linear',
        hover_data={'NO_MUN_MIN': True, 'BALANCA': ':.2f'},
        color_discrete_sequence=paleta_de_cores
    )

    # Se for gráfico por mês, ajustar eixo X com os nomes corretos
    if coluna == 'MES':
        meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        fig.update_xaxes(
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=meses_nomes
        )
    
    # Ajuste dinâmico de ticks no eixo X se houver muitos valores
    if coluna == 'DATA':
        # Dicionário para traduzir mês numérico para abreviação em português
        meses_abreviados_pt = {
            1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
        }

        # Pega os valores únicos e ordenados
        x_vals = sorted(top_cidades[coluna].unique())
        step = len(x_vals) // 12 + 1
        tick_vals = x_vals[::step]

        # Gera os textos formatados: "Jan/2023", "Fev/2023", etc.
        tick_text = [f"{meses_abreviados_pt[val.month]}/{val.year}" for val in tick_vals]

        fig.update_xaxes(
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_text
        )

    # Anotações nos pontos
    for trace in fig.data:
        textos = []
        for y in trace['y']:
            if y >= 1e9:
                textos.append(f'US$ {y / 1e9:.1f}B')
            elif y >= 1e6:
                textos.append(f'US$ {y / 1e6:.1f}M')
            elif abs(y) >= 1e9:
                textos.append(f'US$ {"-" if y < 0 else ""}{abs(y) / 1e9:.1f}B')
            elif abs(y) >= 1e6:
                textos.append(f'US$ {"-" if y < 0 else ""}{abs(y) / 1e6:.1f}M')
            else:
                textos.append(f'US$ {y:,.2f}')
            
        # Atribui os textos ao trace para que apareçam como labels
        trace.hovertext = textos
        trace.textposition = 'top center'
        trace.mode = 'lines+markers+text'
        trace.textfont = dict(size=10, color='black', family='Arial')
        trace.hovertemplate = (
        '<b>%{hovertext}</b><br>' +
        'Ano/Mês: %{x}<br>' +
        'Valor: US$ %{y:,.2f}<extra></extra>'
        )


    # Layout geral
    fig.update_layout(
        title=None,
        annotations = [dict(
            text = f'{periodo_inicial_grafico} - {periodo_final_grafico}',
            x = 0.5,
            y = 1.10, 
            xref = "paper", 
            yref="paper",
            font = dict(
                size = 14
            ),
            showarrow = False
    
        )],
        xaxis_title='Mês' if coluna == 'MES' else 'Ano',
        yaxis_title='Balança Comercial (US$)',
        legend_title='Município',
        font=dict(family='Arial', size=12),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Rockwell"),
        plot_bgcolor='white',
        margin=dict(l=60, r=60, t=60, b=60),
        showlegend=True,
        autosize=True,
        legend=dict(
            orientation="h",
            yanchor="middle",
            y=-1.0,
            xanchor="right",
            x=1,
            font=dict(
                size=10
                ),
            ),
        xaxis=dict(
            tickangle=45
        )
    
    )

    # Grade de fundo com linhas cinza claro
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#eeeeee',
        gridwidth=1
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#eeeeee',
        gridwidth=1
    )

    # Linha de base
    fig.add_shape(
        type="line",
        x0=top_cidades[coluna].min(), x1=top_cidades[coluna].max(),
        y0=0, y1=0,
        line=dict(color="black", width=2, dash="dashdot"),
    )
    if retorno == 'fig': return fig

    # Salvar HTML
    pasta_graficos = os.path.join('graficos-dinamicos', session_id)
    os.makedirs(pasta_graficos, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_graficos, f'balanca_comercial_{session_id}.html')
    fig.write_html(caminho_arquivo)

    return caminho_arquivo


# ------------------------- Método que faz o Gráfico de Todas as Cargas --------------------------------------------

# Função principal da balança comercial por produto
def funil_por_produto(df, df_sh4, tipo, metrica, retorno, session_id,periodo_inicial_grafico,periodo_final_grafico):

    # Agrupa por produto (SH4), somando ou tirando média de acordo com a coluna
    if metrica == 'VL_FOB':
        df_total = agrupar_df(df, ['SH4'], metrica, 'sum')
    elif metrica == 'VALOR AGREGADO':
        df_total = agrupar_df(df, ['SH4'], metrica, 'mean')
    elif metrica == 'KG_LIQUIDO':
        df_total = agrupar_df(df, ['SH4'], metrica, 'sum')

    # Ordena pelo metrica (maior saldo)
    df_total = df_total.sort_values(by=f'{metrica}', ascending=False)

    # Garante que SH4 tenha um único produto associado
    df_sh4_resumo = df_sh4[['SH4', 'PRODUTO']].drop_duplicates(subset='SH4')

    # Mescla com o total de cargas
    df_total = mesclar_df(df_total, df_sh4_resumo, ['SH4'], how='left')

    # Agrupa por SH4 e PRODUTO para evitar duplicação de barras
    df_total = df_total.groupby(['SH4', 'PRODUTO'], as_index=False)[metrica].sum()

    # Cria nome de produto limitado apenas para o eixo Y
    df_total['PRODUTO_LIMITADO'] = df_total['PRODUTO'].str.slice(0, 20) + '...'

    # Seleciona top 20 produtos
    df_total = df_total.sort_values(by=metrica, ascending=False).head(10)

    # Agrupa novamente por PRODUTO_LIMITADO para evitar erro de barras duplicadas
    df_total = df_total.groupby('PRODUTO_LIMITADO', as_index=False).agg({
        metrica: 'sum',
        'PRODUTO': 'first'  # Pega um nome completo representativo
    })

    # Reordena para visualização crescente
    df_total = df_total.sort_values(by=metrica, ascending=True)

    # Paleta de cores
    paleta_de_cores = [
        "#3399ff",  # azul
        "#66b2ff",  # azul médio
        "#99ccff",  # azul claro
        "#cce5ff",  # azul bem claro  
        "#003d80",   # azul bem escuro
        "#0059b3",  # azul escuro
        "#0073e6"  # azul intenso
    ]

    df_total['hover_text'] = (
    "Descrição: " + df_total['PRODUTO'].apply(lambda x: quebrar_texto(x, 60))
    )

    tipo_lower = tipo.lower()

    # Define o rótulo de eixo e o texto do gráfico de acordo com a métrica
    if metrica == 'KG_LIQUIDO': 
        unidade = 'kg' 
        text_template = 'kg %{x:,.0f}' 
    else: 
        unidade = 'US$' 
        text_template = 'US$ %{x:,.0f}' 

    # Gera gráfico de funil com nome completo no hover
    fig = px.funnel(
        df_total,
        y='PRODUTO_LIMITADO',
        x=f'{metrica}',
        title=f'',
        labels={f'{metrica}': f'{tipo} ({unidade})', 'PRODUTO_LIMITADO': 'Produto'},
        color='PRODUTO_LIMITADO',
        hover_name='hover_text',  # Mostra nome completo no tooltip
        hover_data={
            'PRODUTO_LIMITADO': False,  # Remove o truncado do hover
            f'{metrica}': True
        },
        color_discrete_sequence=paleta_de_cores
    )

    # Atualiza rótulos do eixo y
    produtos = df_total['PRODUTO_LIMITADO'].unique()
    produtos_curto = [p[:10] + '...' if len(p) > 10 else p for p in produtos]

    # Layout
    fig.update_layout(
        title_x=0.5,
        annotations = [dict(
            text = f'{periodo_inicial_grafico} - {periodo_final_grafico}',
            x = 0.5,
            y = 1.10, 
            xref = "paper", 
            yref="paper",
            font = dict(
                size = 14
            ),
            showarrow = False
        )],
        font=dict(family='Arial', size=12),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Rockwell"),
        margin=dict(l=60, r=60, t=80, b=60),
        showlegend=False,
        autosize=True,  
        yaxis=dict(
            tickmode='array',
            tickvals=produtos,
            ticktext=produtos_curto
            )
        )

   # Formatação dos valores dentro do funil
    fig.update_traces(texttemplate=text_template, textposition='inside')

    # Retorno em figura ou como caminho do HTML
    if retorno == 'fig':
        return fig

    pasta_graficos = os.path.join('graficos-dinamicos', session_id)
    os.makedirs(pasta_graficos, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_graficos, f'funil_por_produto_{session_id}.html')
    fig.write_html(caminho_arquivo)

    return caminho_arquivo

# ------------------------- Método que faz o Gráfico de Ranking de Municípios --------------------------------------------

def ranking_municipios(df_mun,df_exp,df_imp, tipo,metrica,df_prod,retorno, session_id,periodo_inicial_grafico,periodo_final_grafico):
    
    if(tipo == 'Exportacões'):
        df = adicionar_ano(df_exp)

    elif(tipo == 'Importacões'):
        df = adicionar_ano(df_imp)
    else:
        raise ValueError(f"Tipo inválido: {tipo}")
    
    # Define o rótulo de eixo e o texto do gráfico de acordo com a métrica
    if metrica == 'KG_LIQUIDO': 
        unidade = 'kg' 
        text_template = 'kg {:,.1f}' 
    else: 
        unidade = 'US$' 
        text_template = 'US$ {:,.1f}' 
    
    # Garante que SH4 tenha um único produto associado
    df_sh4_resumo = df_prod[['SH4', 'PRODUTO']].drop_duplicates(subset='SH4')
    df_comp = mesclar_df(df,df_sh4_resumo, ['SH4'])

    # agrupamento
    if(metrica == 'VALOR AGREGADO'):
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'VALOR AGREGADO', 'mean')
        tipo_anos.rename(columns={'VALOR AGREGADO':'VALOR_AGREGADO'}, inplace=True)
        metrica = 'VALOR_AGREGADO'
        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="VALOR_AGREGADO", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['VALOR AGREGADO'].mean()

        cargas_top5 = cargas.sort_values(['CO_MUN','VALOR AGREGADO'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(5)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["VALOR_AGREGADO_FORMAT"] = cargas_top5['VALOR AGREGADO'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = (cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (Valor Agregado da Carga: ' +cargas_top5['VALOR_AGREGADO_FORMAT'] + ')')

        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index()

        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')

        
        

    elif(metrica == 'VL_FOB'):
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'VL_FOB', 'sum')

        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="VL_FOB", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['VL_FOB'].sum()
        cargas.rename(columns={'VL_FOB': 'VL FOB'}, inplace=True)

        cargas_top5 = cargas.sort_values(['CO_MUN','VL FOB'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(5)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["VL_FOB_FORMAT"] = cargas_top5['VL FOB'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (Valor Fob:' + cargas_top5['VL_FOB_FORMAT'].round(2).astype(str) + ')'
        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index()

        
        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')

    elif(metrica == 'KG_LIQUIDO'):
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'KG_LIQUIDO', 'sum')

        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="KG_LIQUIDO", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['KG_LIQUIDO'].sum()
        cargas.rename(columns={'KG_LIQUIDO': 'KG LIQUIDO'}, inplace=True)

        cargas_top5 = cargas.sort_values(['CO_MUN','KG LIQUIDO'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(5)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["KG_LIQUIDO_FORMAT"] = cargas_top5['KG LIQUIDO'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (KG líquido:' + cargas_top5['KG_LIQUIDO_FORMAT'].round(2).astype(str) + ')'
        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index() 

        
        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')


    # Paleta
    paleta_de_cores = [
        "#26517f",
        "#003d80",   # azul bem escuro
        "#0059b3",  # azul escuro
        "#0073e6",  # azul intenso
        "#3399ff",  # azul
        "#00bdf2",
        "#71b2e1",
        "#66b2ff",  # azul médio
        "#99ccff",  # azul claro
        "#cce5ff"  # azul bem claro  
    ]


    # Gráfico
    fig = px.bar(
        municipios_total,
        x='NO_MUN_MIN',
        y=f'{metrica}',
        color='NO_MUN_MIN',
        # title=f'Top 10 municípios por {metrica} de {tipo}',
        labels={'NO_MUN_MIN': 'Município'},
        hover_data = {'CO_MUN': False,f'{metrica}':True,'NO_MUN_MIN':True, 'descricao':True},
        color_discrete_sequence=paleta_de_cores,
    )

    # Layout geral
    fig.update_layout(
        title=None,
        annotations = [dict(
            text = f'{periodo_inicial_grafico} - {periodo_final_grafico}',
            x = 0.5,
            y = 1.10, 
            xref = "paper", 
            yref="paper",
            font = dict(
                size = 14
            ),
            showarrow = False
        )],
        yaxis=dict(
            title=f'{metrica}',
            tickformat=',.2s' if metrica == 'VALOR_AGREGADO' else None,
            ticksuffix = f' {unidade}'
        ),
        legend_title='Município',
        font=dict(family='Arial', size=12),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Rockwell"),
        plot_bgcolor='white',
        margin=dict(l=60, r=60, t=60, b=80),
        showlegend=True,
        autosize=True,
        legend=dict(
            orientation="h",
            yanchor="middle",
            y=-1.5,
            xanchor="right",
            x=1,
            font=dict(
                size=9
                ),
            ),
        xaxis=dict(
            tickangle=45
        )
    )

    if retorno == 'fig': return fig

    # Salvar HTML
    pasta_graficos = os.path.join('graficos-dinamicos', session_id)
    os.makedirs(pasta_graficos, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_graficos, f'ranking_municipios_{session_id}.html')
    fig.write_html(caminho_arquivo)

    return caminho_arquivo
    


def ranking_municipios_cargas(df_mun,df_exp,df_imp, tipo,metrica,df_prod,retorno, session_id,periodo_inicial_grafico,periodo_final_grafico):
    
    if(tipo == 'Exportacões'):
        df = adicionar_ano(df_exp)

    elif(tipo == 'Importacões'):
        df = adicionar_ano(df_imp)
    else:
        raise ValueError(f"Tipo inválido: {tipo}")
    
    # Define o rótulo de eixo e o texto do gráfico de acordo com a métrica
    if metrica == 'KG_LIQUIDO': 
        unidade = 'kg' 
        text_template = 'kg {:,.1f}' 
    else: 
        unidade = 'US$' 
        text_template = 'US$ {:,.1f}' 
    
    # Garante que SH4 tenha um único produto associado
    df_sh4_resumo = df_prod[['SH4', 'PRODUTO']].drop_duplicates(subset='SH4')
    df_comp = mesclar_df(df,df_sh4_resumo, ['SH4'])

    # agrupamento
    if(metrica == 'VALOR AGREGADO'):
        # nessa estou separando por cargas
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'VALOR AGREGADO', 'mean')
        tipo_anos.rename(columns={'VALOR AGREGADO':'VALOR_AGREGADO'}, inplace=True)
        metrica = 'VALOR_AGREGADO'
    
        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="VALOR_AGREGADO", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['VALOR AGREGADO'].mean()

        cargas_top5 = cargas.sort_values(['CO_MUN','VALOR AGREGADO'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(30)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["VALOR_AGREGADO_FORMAT"] = cargas_top5['VALOR AGREGADO'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = (cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (Valor Agregado da Carga: ' +cargas_top5['VALOR_AGREGADO_FORMAT'] + ')')
  
        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index()
        
        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')
        

    elif(metrica == 'VL_FOB'):
        # nesse está o hover com 30 cargas
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'VL_FOB', 'sum')

        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="VL_FOB", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['VL_FOB'].sum()
        cargas.rename(columns={'VL_FOB': 'VL FOB'}, inplace=True)

        cargas_top5 = cargas.sort_values(['CO_MUN','VL FOB'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(30)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["VL_FOB_FORMAT"] = cargas_top5['VL FOB'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (Valor Fob:' + cargas_top5['VL_FOB_FORMAT'].round(2).astype(str) + ')'

        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index()

        
        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')

    elif(metrica == 'KG_LIQUIDO'):
        # neste está igual o grafico só de ranking municipios, não tinha mexido nesse
        tipo_anos = agrupar_df(df_comp,['CO_MUN'], 'KG_LIQUIDO', 'sum')

        # Adiciona o nome dos municípios
        municipios = mesclar_df(tipo_anos, df_mun[['CO_MUN', 'NO_MUN_MIN']], ['CO_MUN'])
        municipios_top10 = municipios.sort_values(by="KG_LIQUIDO", ascending=False).head(10)  

        cargas = df_comp.groupby(['CO_MUN', 'SH4','PRODUTO'],as_index=False)['KG_LIQUIDO'].sum()
        cargas.rename(columns={'KG_LIQUIDO': 'KG LIQUIDO'}, inplace=True)

        cargas_top5 = cargas.sort_values(['CO_MUN','KG LIQUIDO'], ascending=False)
        cargas_top5 = cargas_top5.groupby('CO_MUN').head(30)

        cargas_top5['PRODUTO_LIMITADO'] = cargas_top5['PRODUTO'].str.slice(0, 30) + '...'

        cargas_top5["KG_LIQUIDO_FORMAT"] = cargas_top5['KG LIQUIDO'].apply(lambda x:text_template.format(x))

        cargas_top5['descricao'] = cargas_top5['SH4'].astype(str) + ' - ' + cargas_top5['PRODUTO_LIMITADO'] + ' - (KG líquido:' + cargas_top5['KG_LIQUIDO_FORMAT'].round(2).astype(str) + ')'

        carga_agrupada = cargas_top5.groupby('CO_MUN')['descricao'].apply(lambda x: '<br>'.join(x)).reset_index() 

        
        municipios_total = pd.merge(municipios_top10, carga_agrupada, on='CO_MUN', how='left')


    # Paleta
    paleta_de_cores = [
        "#26517f",
        "#003d80",   # azul bem escuro
        "#0059b3",  # azul escuro
        "#0073e6",  # azul intenso
        "#3399ff",  # azul
        "#00bdf2",
        "#71b2e1",
        "#66b2ff",  # azul médio
        "#99ccff",  # azul claro
        "#cce5ff"  # azul bem claro  
    ]

    # Gráfico
    fig = px.bar(
        municipios_total,
        x='NO_MUN_MIN',
        y=f'{metrica}',
        color='descricao',
        title=f'Top 10 municípios por {metrica} de {tipo}',
        labels={'NO_MUN_MIN': 'Município'},
        hover_data = {'CO_MUN': False,f'{metrica}':True,'NO_MUN_MIN':True, 'descricao':True},
        color_discrete_sequence=paleta_de_cores,
    )

    # Layout geral
    fig.update_layout(
        title=None,
        annotations = [dict(
            text = f'{periodo_inicial_grafico} - {periodo_final_grafico}',
            x = 0.5,
            y = 1.05, 
            xref = "paper", 
            yref="paper",
            font = dict(
                size = 14
            ),
            showarrow = False
    
        )],
        yaxis=dict(
            title=f'{metrica}',
            tickformat=',.2s' if metrica == 'VALOR_AGREGADO' else None,
            ticksuffix = f' {unidade}'
        ),
        legend_title='Município',
        font=dict(family='Arial', size=12),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Rockwell"),
        plot_bgcolor='white',
        margin=dict(l=60, r=60, t=60, b=60),
        showlegend=False,
        xaxis=dict(
            tickangle=45
        )
    )

    if retorno == 'fig': return fig

    # Salvar HTML
    pasta_graficos = os.path.join('graficos-dinamicos', session_id)
    os.makedirs(pasta_graficos, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_graficos, f'ranking_municipios_cargas_{session_id}.html')
    fig.write_html(caminho_arquivo)

    return caminho_arquivo

def municipio_cargas(df, df_mun, df_sh4, cidade, tipo, metrica, retorno, session_id):
    df_cidade = df[df['CO_MUN'] == cidade]

    if metrica == 'VALOR AGREGADO':
        # Agrupando por 'SH4' e calculando a média do 'VALOR AGREGADO'
        df_group = df_cidade.groupby('SH4')[metrica].mean().reset_index()

    elif metrica == 'VL_FOB' or metrica == 'KG_LIQUIDO':
        # Agrupando por 'SH4' e calculando a soma da métrica
        df_group = df_cidade.groupby('SH4')[metrica].sum().reset_index()
    
    # Adiciona o código do município para possibilitar o merge
    df_group['CO_MUN'] = cidade  # Agora a coluna 'CO_MUN' está presente
        
    # Ordenando as cargas pela métrica de forma crescente
    df_group = df_group.sort_values(by=metrica, ascending=True)

    # Ordenando o df_final pela ordem dos municípios conforme top_municipios
    df_final  = df_group.sort_values(by=metrica, ascending=False)

    # Junta com os nomes dos municípios e produtos
    df_final = df_final.merge(df_mun[['CO_MUN', 'NO_MUN_MIN']], on='CO_MUN', how='left')
    df_final = df_final.merge(df_sh4[['SH4', 'PRODUTO']], on='SH4', how='left')

    # Paleta
    paleta_de_cores = [
        "#26517f",
        "#003d80",   # azul bem escuro
        "#0059b3",  # azul escuro
        "#0073e6",  # azul intenso
        "#3399ff",  # azul
        "#00bdf2",
        "#71b2e1",
        "#66b2ff",  # azul médio
        "#99ccff",  # azul claro
        "#cce5ff"  # azul bem claro  
    ]
    nome_municipio = df_final['NO_MUN_MIN'].iloc[0] if not df_final.empty else 'Município Desconhecido'

    # Cálculo da porcentagem para cada linha
    df_final['Porcentagem'] = (df_final[metrica] / df_final[metrica].sum()) * 100

    # Função para converter valores em FOB para dólares e formatar adequadamente
    def formatar_valor_fob(valor):
        if valor >= 1e9:
            return f"{valor / 1e9:.2f}B"  # Bilhões
        elif valor >= 1e6:
            return f"{valor / 1e6:.2f}M"  # Milhões
        else:
            return f"{valor:.2f}"  # Valores menores que milhão

    # Converter a métrica (VALOR FOB) para formato de dólares
    df_final['Valor'] = df_final[metrica].apply(formatar_valor_fob)

    # Função para limitar o nome do produto a no máximo 4 palavras
    def limitar_nome_produto(nome_produto):
        palavras = nome_produto.split()[:4]  # Limita a 4 palavras
        return  ' '.join(palavras) + '...'

    # Aplicar a função de limitação ao nome do produto
    df_final['Produto Resumido'] = df_final['PRODUTO'].apply(limitar_nome_produto)

    # Gráfico tipo treemap
    fig = px.treemap(
        df_final,
        path=['NO_MUN_MIN', 'Produto Resumido'],  # Hierarquia: primeiro município, depois produto resumido
        values=metrica,  # A métrica será a área das caixas
        hover_data={'CO_MUN': False, 'Valor': True, metrica: True, 'NO_MUN_MIN': True, 'PRODUTO': True},  # Informações ao passar o mouse
        color='PRODUTO',  # Cor por produto
        color_discrete_sequence=paleta_de_cores,  # Sua paleta de cores
    )

    # Garantir que o título aparece e definir a cor como branca
    fig.update_layout(
        title=f'',
        title_font=dict(size=46, color='white'),  # Título com fonte maior e cor branca
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Rockwell"),
        )

    # Adicionando o texto na caixa para mostrar o produto, o valor convertido e a porcentagem
    fig.update_traces(
        textinfo="label+value+percent entry",  # Exibe o nome do produto, o valor e a porcentagem
        text=df_final['Valor'] + " " + df_final['Porcentagem'].apply(lambda x: f"{x:.2f}%"),  # Adiciona o texto personalizado com valor convertido e porcentagem
        textfont=dict(size=50, color='white'),  # Aumenta o tamanho da fonte da porcentagem
        textposition="middle center",  # Centraliza o texto nas caixas
    )


    if retorno == 'fig': return fig

    # Salvar HTML
    pasta_graficos = os.path.join('graficos-dinamicos', session_id)
    os.makedirs(pasta_graficos, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_graficos, f'municipio_cargas_{session_id}.html')
    fig.write_html(caminho_arquivo)

    return caminho_arquivo
