def red_parser(response):
    resultado = []

    for servicio in response['servicios']['item']:
        indices = []
        for key in servicio.keys():
            if key.startswith('distanciabus'):
                index = key.replace('distanciabus', '')
                if index.isdigit():
                    indices.append(int(index))
        
        indices.sort()
        
        for i in indices:
            distancia = servicio.get(f'distanciabus{i}')
            prediccion = servicio.get(f'horaprediccionbus{i}')
            resultado.append({
                'servicio': servicio['servicio'],
                'distancia': distancia,
                'prediccion': prediccion
            })
    print(resultado)
    return resultado


def reply_text(parsed_response):
    formated = []
    for bus in parsed_response:
        formated.append(f"🚍 {bus["servicio"]} {bus["distancia"]}m ({bus["prediccion"]})")
    sep = [15*"➖"]
    print("\n".join(formated))
    return "\n".join(sep + formated + sep)
