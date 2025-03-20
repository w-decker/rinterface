from .rinterface import rinterface
from .utils import to_r
import subprocess
from . import backend as bk

def is_r_installed():
    try:
        result = subprocess.run(['Rscript', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    
if not is_r_installed():
    raise RuntimeError("Rscript is not installed on your system. Please install R to use this package.")

if bk.command == "apptainer" and bk.apptainer_path is None:
    raise ValueError("If using Apptainer, please set the path to the Apptainer executable in rinterface.backend.apptainer_path")

__all__ = ["rinterface", "to_r"]