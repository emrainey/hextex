"""
Hextex module. A textual hexadecimal viewer for binary files.
"""

__version__ = "0.1.0"
__author__ = "Erik Rainey"

# Import key classes/functions to make them available at package level
# from .core import SomeClass
# from .utils import some_function

# Define what gets imported with "from hextex import *"
# __all__ = ["SomeClass", "some_function"]

from .tui import HexTex  # noqa: F401
from .bin import BinFile  # noqa: F401

__all__ = ["HexTex", "BinFile"]
