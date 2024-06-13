from . import blendermania
from . import tools_script
from . import Detection
from . import CustomTexture

def register_external():
    blendermania.register()
    tools_script.register()
    Detection.register()
    CustomTexture.register()

def unregister_external():
    blendermania.unregister()
    tools_script.unregister()
    Detection.unregister()
    CustomTexture.unregister()
