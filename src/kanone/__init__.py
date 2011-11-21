from .validator import *
from .lib import MISSING, Context

import pkg_resources as __pkg_resources__
__pkg_resources__.declare_namespace(__name__)
__version__ = __pkg_resources__.require("kanone")[0].version
