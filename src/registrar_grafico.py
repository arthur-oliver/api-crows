def registrar(filtros: dict, caminhos: list):
    import os, json
    CAMINHO_REGISTRO = '.registros_graficos'
    registros = {}

    if os.path.exists(CAMINHO_REGISTRO):
        with open(CAMINHO_REGISTRO, 'r') as f:
            try:
                registros = json.load(f)
            except json.JSONDecodeError:
                registros = {}

    chave = json.dumps(filtros, sort_keys=True)
    registros[chave] = caminhos

    with open(CAMINHO_REGISTRO, 'w') as f:
        json.dump(registros, f, indent=2)
