# command_handler.py

COMMANDS = {
    "<<QUERY:POSITION>>": lambda: "[OPERARIO]\nPosición solicitada.",
    "<<QUERY:INFO>>":     lambda: "[OPERARIO]\nSoy un robot de rescate Summit XL. Detecto víctimas y recibo órdenes.",
    "<<MOVE:derecha>>":   lambda: "[OPERARIO]\nMovimiento ejecutado: derecha.",
    "<<MOVE:izquierda>>": lambda: "[OPERARIO]\nMovimiento ejecutado: izquierda.",
    "<<MOVE:adelante>>":  lambda: "[OPERARIO]\nMovimiento ejecutado: adelante.",
    "<<MOVE:atras>>":     lambda: "[OPERARIO]\nMovimiento ejecutado: atrás.",
}


def handle(response: str, robot_position: dict = None) -> str:
    
    if "<<QUERY:POSITION>>" in response:
        if robot_position:
            pos = robot_position
            return "[OPERARIO]\nUnidad Summit XL en coordenadas x={x}, y={y}.".format(**pos)
        else:
            return "[OPERARIO]\nPosición del robot no disponible aún."

    for keyword, action in COMMANDS.items():
        if keyword in response:
            return action()
    return response
