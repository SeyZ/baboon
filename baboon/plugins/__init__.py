import os
from pkgutil import iter_modules

__all__ = []

# Adds all valid modules in the 'baboon/plugins/' directory in the
# __all__ variable
for module in iter_modules([os.path.dirname(__file__)]):
    if module[2]:  # if it's a valid python module
        # Adds the name of the module directory to the __all__
        # variable
        __all__.append(module[1])
