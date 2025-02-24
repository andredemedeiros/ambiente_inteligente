import requests

# Defina a URL
#url = 'http://127.0.0.1:8000/set-device-state/D/true'

url = 'http://34.224.87.71:8000/set-device-state/B/true'


# Envie a requisição POST
response = requests.post(url)

# Verifique a resposta
if response.status_code == 200:
    print("Requisição bem-sucedida!")
    print("Conteúdo retornado pelo servidor:")
    print(response.text)  # Imprime o conteúdo retornado como texto
else:
    print(f"Erro na requisição: {response.status_code}")
    print("Conteúdo retornado pelo servidor:")
    print(response.text)  # Imprime o conteúdo retornado em caso de erro
