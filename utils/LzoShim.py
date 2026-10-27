import sys
import types

from . import MiniLzo as mini_lzo

# tmunlimiter_blender_plugin fait `import lzo` (python-lzo), qui n'a pas de wheel pour
# Blender 5.x (Python 3.13). On fournit un module `lzo` de remplacement, basé sur le
# portage pur Python de minilzo, avec la même API que python-lzo :
#   compress(data, level=1, header=True) / decompress(data, header=True, buflen=None)
# Avec header=True, python-lzo préfixe les données par 0xF0 + taille décompressée (big endian).


def _compress(data, level=1, header=True):
    data = bytes(data)
    out = mini_lzo.compress(data)
    if header:
        out = b"\xf0" + len(data).to_bytes(4, "big") + out
    return out


def _decompress(data, header=True, buflen=None):
    data = bytes(data)
    if header:
        buflen = int.from_bytes(data[1:5], "big")
        data = data[5:]
    if buflen is None:
        raise ValueError("buflen is required when header=False")
    return mini_lzo.decompress(data, buflen)


def install():
    """Rend `import lzo` disponible, sauf si le vrai python-lzo est installé."""
    if "lzo" in sys.modules:
        return
    try:
        import lzo  # noqa: F401  (vrai python-lzo)
        return
    except ImportError:
        pass

    module = types.ModuleType("lzo")
    module.__doc__ = "TM Unlimiter Tool: python-lzo replacement based on mini_lzo"
    module.compress = _compress
    module.decompress = _decompress
    module.tmu_shim = True
    sys.modules["lzo"] = module


def uninstall():
    module = sys.modules.get("lzo")
    if module is not None and getattr(module, "tmu_shim", False):
        del sys.modules["lzo"]
