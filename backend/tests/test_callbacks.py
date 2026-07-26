import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyenergyplus.api import EnergyPlusAPI

api = EnergyPlusAPI()
callbacks = [d for d in dir(api.runtime) if "callback" in d]
for c in callbacks:
    print(c)
