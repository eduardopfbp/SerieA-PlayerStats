import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import numpy as np

# Carrega o DataFrame com os links
link = pd.read_csv('C://Users//eduar//Desktop//DEV//Football//SerieA//links.csv')

# Prefixo para os links
prefixo = "https://fbref.com"

# Lista para armazenar os DataFrames
dataframes = [] 

# Data de início para extração
data_inicio = datetime.strptime('2024-09-14', '%Y-%m-%d')

# Número máximo de tentativas falhadas
max_falhas = 2
falhas = 0

# Função para extrair os dados de uma tabela
def extrair_tabela(rows):
    headers = []
    data = []

    for row in rows:
        # Ignora as linhas com a classe "over_header"
        if 'over_header' in row.get('class', []):
            continue

        # Verifica se a linha é de cabeçalho ou de dados
        cols = row.find_all(['th', 'td'])
        if len(headers) == 0:  # Primeira linha após "over_header" será o cabeçalho
            headers = [col.get_text(strip=True) for col in cols]
        else:  # Demais linhas são dados
            data.append([col.get_text(strip=True) for col in cols])

    # Cria o DataFrame
    return pd.DataFrame(data, columns=headers)

# Itera sobre cada linha do DataFrame link
for _, row in link.iterrows():
    data_jogo = row['Data']  # Data do jogo
    
    # Verifica se a data do jogo é posterior ou igual à data de início
    if pd.to_datetime(data_jogo) >= data_inicio:
        url_relatorio = prefixo + row['Link Relatório']  # Concatena o prefixo com o link

        try:
            # Pausa de 4 segundos antes de cada requisição
            time.sleep(4)
            
            # Faz a requisição para a página
            response = requests.get(url_relatorio)
            response.raise_for_status()  # Levanta um erro para códigos de status HTTP 4xx/5xx
            soup = BeautifulSoup(response.content, "html.parser")

            # Encontra o div com id "content" e role="main"
            content_div = soup.find('div', id='content', role='main')

            # Extrai o primeiro <h1> que contém os times
            h1_text = content_div.find('h1').get_text(strip=True)

            # Divide o texto do <h1> no "vs."
            times = h1_text.split(' vs. ')
            if len(times) != 2:
                print(f"Erro ao extrair times da partida no relatório: {url_relatorio}")
                continue

            # Primeiro time antes do "vs."
            primeiro_time = times[0].strip()

            # Segundo time, parte após "vs." até "Relatório"
            segundo_time = times[1].split(' Relatório')[0].strip()

            # Encontra todos os containers de tabelas
            table_containers = soup.select('div.table_container')

            # Lista para armazenar as tabelas desejadas
            tabelas_desejadas = []
            
            # Adiciona a primeira tabela (do primeiro time)
            if len(table_containers) > 0:
                rows = table_containers[0].find_all('tr')
                tabela = extrair_tabela(rows)
                tabela['Data'] = data_jogo
                tabela['Time'] = primeiro_time  # Adiciona o nome do primeiro time
                tabelas_desejadas.append(tabela)
                
            # Adiciona a oitava tabela (do segundo time)
            if len(table_containers) > 7:
                rows = table_containers[7].find_all('tr')
                tabela = extrair_tabela(rows)
                tabela['Data'] = data_jogo
                tabela['Time'] = segundo_time  # Adiciona o nome do segundo time
                tabelas_desejadas.append(tabela)

            # Adiciona os DataFrames desejados à lista, ignorando vazios
            dataframes.extend([t for t in tabelas_desejadas if not t.empty])

            # Reseta o contador de falhas após sucesso
            falhas = 0

        except requests.RequestException as e:
            print(f"Erro ao acessar {url_relatorio}: {e}")
            falhas += 1

            # Verifica se o número máximo de falhas foi atingido
            if falhas >= max_falhas:
                print("Número máximo de falhas atingido. Encerrando a execução.")
                break

        except Exception as e:
            print(f"Erro inesperado: {e}")
            falhas += 1

            # Verifica se o número máximo de falhas foi atingido
            if falhas >= max_falhas:
                print("Número máximo de falhas atingido. Encerrando a execução.")
                break

# Verifica se há DataFrames para concatenar
if dataframes:
    # Concatena todos os DataFrames em um único DataFrame
    df_final = pd.concat(dataframes, ignore_index=True)

    # Mover a última coluna para a segunda posição
    cols = list(df_final.columns)
    cols.insert(1, cols.pop(-1))  # Remove a última coluna e insere na segunda posição
    df_final = df_final[cols]

    # Validação da coluna 'Nação'
    def remove_lowercase(value):
        if isinstance(value, str):
            return re.sub(r'[a-z]', '', value)
        return value

    # Aplicar a função à coluna 'Nação'
    df_final['Nação'] = df_final['Nação'].apply(remove_lowercase)

    # Tratamento de nulos: substituir valores vazios e espaços em branco por NaN
    df_final['#'] = df_final['#'].replace('', np.nan).replace(' ', np.nan).replace(r'^\s*$', np.nan, regex=True)

    # Remover linhas onde a coluna '#' tem valor NaN
    df_final = df_final.dropna(subset=['#'])

    print(df_final)

    # Salva o DataFrame final em um arquivo Excel
    df_final.to_csv('C://Users//eduar//Desktop//DEV//Football//SerieA//database_temp.csv', index=False)
else:
    print("Nenhum DataFrame para concatenar.")
