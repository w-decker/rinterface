import numpy as np
import pandas as pd

def to_r(value):
    """Convert Python value to R"""
    if isinstance(value, np.ndarray):
        return _from_numpy(value)
    elif isinstance(value, pd.DataFrame):
        return _from_pandas(value)
    elif isinstance(value, str):
        return _from_str(value)
    elif isinstance(value, bool): 
        return _from_bool(value)
    else:
        raise ValueError(f"Unsupported type: {type(value)}")

def _from_numpy(value:np.ndarray):
    """Convert numpy array to R"""
    if value.ndim == 1:
        return f"c({','.join(map(str,value))})"
    elif value.ndim == 2:
        flat_array = value.flatten(order="F")
        r_vector = ", ".join(map(str, flat_array))
        nrow, ncol = value.shape
        return f"matrix(c({r_vector}), nrow = {nrow}, ncol = {ncol}, byrow = FALSE)"
    elif value.ndim > 2:
        flat_array = value.flatten(order="F")
        r_vector = ", ".join(map(str, flat_array))
        shape = ", ".join(map(str, value.shape))
        return f"array(c({r_vector}), dim = c({shape}))"
    
def _from_pandas(value:pd.DataFrame):
    """Convert pandas DataFrame to R"""
    r_columns = []
    for col in value.columns:
        col_name = f"`{col}`"  # Backticks ensure column names are always valid in R, even with spaces or special characters
        values = value[col].replace({np.nan: "NA"}).tolist()  # Replace NaN with NA (R's missing value)
        if pd.api.types.is_numeric_dtype(value[col]):
            r_col = f"{col_name} = c({', '.join(map(str, values))})"
        else:
            value_str = ', '.join(f'"{str(v)}"' for v in values)
            r_col = f"{col_name} = c({value_str})"
        r_columns.append(r_col)
    return f"data.frame({', '.join(r_columns)})"

def _from_str(value:str):
    """Convert string to R"""
    return f'"{value}"'

def _from_bool(value:bool):
    """Convert bool to R"""
    return "TRUE" if value else "FALSE"