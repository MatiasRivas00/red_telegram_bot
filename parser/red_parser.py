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
    return resultado


def reply_text(parsed_response):
    formated = []
    for bus in parsed_response:
        distancia = f"{bus["distancia"]}m" if bus["distancia"] else "💤"
        prediccion = f"({bus["prediccion"]})" if bus["prediccion"]  else "💤"
        servicio = bus["servicio"]
        formated.append(f"🚍 {servicio} {distancia} {prediccion}")
    sep = [15*"➖"]
    return "\n".join(sep + formated + sep)
