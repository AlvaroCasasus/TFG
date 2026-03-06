# Aquí se conectarían las llamadas reales al robot (ROS, API, etc.)

COMMANDS = {
    "<<QUERY:POSITION>>": lambda: "[OPERARIO]\nUnidad Summit XL en Sector Alpha, punto de entrada.",
    "<<QUERY:INFO>>": lambda: "[OPERARIO]\nSoy un robot de rescate Summit XL. Detecto víctimas y recibo órdenes.",
    "<<MOVE:derecha>>":    lambda: "[OPERARIO]\nMovimiento ejecutado: derecha.",
    "<<MOVE:izquierda>>":  lambda: "[OPERARIO]\nMovimiento ejecutado: izquierda.",
    "<<MOVE:adelante>>":   lambda: "[OPERARIO]\nMovimiento ejecutado: adelante.",
    "<<MOVE:atras>>":      lambda: "[OPERARIO]\nMovimiento ejecutado: atrás.",
}

def handle(response: str) -> str:
    for keyword, action in COMMANDS.items():
        if keyword in response:
            return action()
    return response
