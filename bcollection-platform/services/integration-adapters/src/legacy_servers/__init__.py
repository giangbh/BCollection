from .core_server import app as core_app
from .los_server import app as los_app
from .cic_server import app as cic_app
from .cti_server import app as cti_app
from .speech_server import app as speech_app
from .messaging_server import app as messaging_app
from .gateway import app as gateway_app

__all__ = ["core_app", "los_app", "cic_app", "cti_app", "speech_app", "messaging_app", "gateway_app"]
