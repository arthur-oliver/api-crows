def consultar(filtros: dict):
    import os, json
    CAMINHO_REGISTRO = '.registros_graficos'

    if not os.path.exists(CAMINHO_REGISTRO):
        return None

    with open(CAMINHO_REGISTRO, 'r') as f:
        try:
            registros = json.load(f)
        except json.JSONDecodeError:
            return None

    chave = json.dumps(filtros, sort_keys=True)
    return registros.get(chave)
