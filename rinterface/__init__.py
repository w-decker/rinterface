from .rinterface import rinterface
import subprocess

def is_r_installed():
    try:
        result = subprocess.run(['Rscript', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    
if not is_r_installed():
    raise RuntimeError("Rscript is not installed on your system. Please install R to use this package.")

__all__ = ["rinterface"]