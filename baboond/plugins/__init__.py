import os
import pkgutil

# Get the package plugins path.
pkgpath = os.path.dirname(__file__)

# Iterate on all package plugins modules.
for imp, mod_name, is_pkg in pkgutil.iter_modules([pkgpath]):
    # Import the current plugin.
    __import__('plugins.' + mod_name)
