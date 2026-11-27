"""Excepciones propias, para poder mostrar errores claros al usuario."""

class AmigoInvisibleError(Exception):
    """Base de todos los errores controlados de la aplicación."""


class ConfigError(AmigoInvisibleError):
    """Configuración ausente o inválida (por ejemplo, faltan las credenciales SMTP)."""


class ParticipantsError(AmigoInvisibleError):
    """El archivo de participantes no existe o contiene datos inválidos."""


class DrawError(AmigoInvisibleError):
    """No es posible realizar el sorteo con las restricciones indicadas."""
