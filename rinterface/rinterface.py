"""
Single, all purpose function for interfacing with R with Python.

At its most basic implementation `rinterface()` takes in a "script" of R-valid code, generates a temporary file (`"temp.R"`), evaluates the script using the `Rscript` command-line tool and then deletes the temporary file. 

You can also "capture" the output from your R script. This returns the output as a formatted string.

Although seeing the output of your R script in your IPython environment is convienent, it is limiting. Sometimes you might need to access the values generated in your R script. You can access these values using a simple heuristic: `# @grab{type}`. Here's how to do it: 1) assign the value you want to a variable. 2) On the line above this variable, write the "tag": `# @grab{type}` and input the type (e.g., `str`, `int`, `float`, etc.) that you wish to load in the variable as. 

"""

import subprocess
import re
import os
import numpy as np
import pandas as pd
from typing import Any
import uuid

def rinterface(
                code: str,
                save: bool = False, 
                fname: str = None,
                capture: bool = False,
                grab: bool = False
               ):
    """
    Execute R-valid code with Python

    Parameters
    ----------
    code: str
        The R code to be executed.
    save: bool, optional
        Whether to save the R code to a file. Default is False.
    fname: str, optional
        The filename to save the R code if save is True. Default is None.
    capture: bool, optional
        Whether to capture stdout/stderr of the R script. Default is False.
    grab: bool, optional
        Whether to extract variables using # @grab{...} lines. Default is False.

    Returns
    -------
    Any or subprocess.CompletedProcess or None
        - If `grab=True`, returns the extracted variable(s).
        - If `capture=True` (and not grabbing variables), returns `CompletedProcess`.
        - Otherwise, returns None.
    """
    temp_file = ".temp.R"
    temp_output = ".grab_output.txt"
    annotated_lines = []
    if grab:
        annotated_lines = re.findall(r"#\s*@grab\{([^}]+)\}\n(.+)", code)
    grab_snippet = ""
    for var_type, var_def in annotated_lines:
        # this is how variables are extracted
        snippet = f"""
        # For variable: {var_def}, type={var_type}
        if (is.data.frame({var_def})) {{
        # Make a unique filename for this data frame
        df_filename <- paste0(".grab_df_", make.names("{var_def}"), "_", "{uuid.uuid4().hex}", ".csv")
        # Write a line "varName=DATAFRAME:.grab_df_xyz.csv"
        cat("{var_def}=DATAFRAME:", df_filename, "\\n", file="{temp_output}", append=TRUE)
        # Write the data frame to that CSV
        write.csv({var_def}, file=df_filename, row.names=FALSE)
        }} else if (is.matrix({var_def})) {{
        dims <- dim({var_def})
        cat("{var_def}=", file="{temp_output}", append=TRUE)
        cat(paste0(dims[1], "x", dims[2], ":"), file="{temp_output}", append=TRUE)
        cat(paste({var_def}, collapse=","), file="{temp_output}", append=TRUE)
        cat("\\n", file="{temp_output}", append=TRUE)
        }} else if (is.vector({var_def})) {{
        cat("{var_def}=", file="{temp_output}", append=TRUE)
        cat(paste({var_def}, collapse=","), file="{temp_output}", append=TRUE)
        cat("\\n", file="{temp_output}", append=TRUE)
        }} else {{
        # fallback for scalar/string/factor
        cat("{var_def}=", file="{temp_output}", append=TRUE)
        cat(as.character({var_def}), file="{temp_output}", append=TRUE)
        cat("\\n", file="{temp_output}", append=TRUE)
        }}
        """
        grab_snippet += snippet
    if grab_snippet:
        code += "\n\n# Appended grab-snippet\n" + grab_snippet

    try:

        # Write temporary R script
        with open(temp_file, "w") as f:
            f.write(code)

        # Optionally save user-provided file
        if save:
            if not fname:
                raise ValueError("If 'save' is True, 'fname' cannot be None.")
            with open(fname, "w") as f_out:
                f_out.write(code)

        # Run R script
        if capture:
            # Capture all output in a CompletedProcess
            results = subprocess.run(
                ["Rscript", temp_file],
                text=True,
                capture_output=True,
                check=True
            )
        else:
            subprocess.run(
                ["Rscript", temp_file],
                text=True,
                capture_output=False,
                check=True
            )

        # If user wants raw captured output (and isn't grabbing variables)
        if grab is False and capture is True:
            return results

        # If not grabbing variables, return None
        if grab is False:
            return None
        if not os.path.exists(temp_output):
            # Means R might have crashed or no variables were actually written
            return None

        with open(temp_output, "r") as f:
            grabbed_lines = f.readlines()

        # Parse each line with parse_r_output, using the declared type
        parsed = []
        for (var_type, var_def), line in zip(annotated_lines, grabbed_lines):
            parsed.append(parse_r_output(line.strip(), var_type))

        # Return single item or tuple
        if len(parsed) == 1:
            return parsed[0]
        return tuple(parsed)

    except subprocess.CalledProcessError as e:
        # Show the real error from R (stderr) for debugging
        msg = f"R script execution failed (exit code={e.returncode}):\n"
        msg += f"--- R stderr ---\n{e.stderr}\n"
        msg += f"--- R stdout ---\n{e.stdout}\n"
        raise RuntimeError(msg)

    finally:
        # Clean up temporary files
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(temp_output):
            os.remove(temp_output)


def parse_r_output(line: str, expected_type: str) -> Any:
    """
    Convert a single line of R output into the Python type declared by @grab{...}.
    Supported types: float, int, str, list[int], list[float], list[str], np.ndarray, pd.DataFrame.
    Parameters
    ----------
    line : str
        e.g. "my_df=2x3::colA,colB,colC::1,2,3,4,5,6"
    expected_type : str
        e.g. "pd.DataFrame", "np.ndarray", "float", "int", "list[int]", ...

    Returns
    -------
    The parsed Python object (DataFrame, ndarray, float, int, etc.).
    """
    # Split on the first '=' to get the variable name and the data string
    if '=' not in line:
        raise ValueError(f"Cannot parse line (no '=' found): {line}")
    var_name, value_str = line.split('=', 1)
    value_str = value_str.strip()

    if expected_type == "float":
        return float(value_str)
    elif expected_type == "int":
        return int(value_str)
    elif expected_type == "str":
        return value_str

    # If it's a list[...] type
    if expected_type.startswith("list["):
        subtype = expected_type[5:-1].strip()  # 'int', 'float', 'str'
        if not value_str:
            return []
        items = value_str.split(',')
        if subtype == "int":
            return list(map(int, items))
        elif subtype == "float":
            return list(map(float, items))
        elif subtype == "str":
            return list(items)
        else:
            raise ValueError(f"Unsupported list element type '{subtype}'")

    # Handle np.ndarray
    if expected_type == "np.ndarray":
        if ':' in value_str and 'x' in value_str:
            shape_part, array_part = value_str.split(':', 1)
            rows_cols = shape_part.split('x')
            if len(rows_cols) != 2:
                raise ValueError(f"Invalid matrix shape in line: {line}")
            nrows, ncols = map(int, rows_cols)
            if not array_part.strip():
                data = []
            else:
                data = list(map(float, array_part.split(',')))
            if len(data) != nrows * ncols:
                raise ValueError("Matrix data does not match shape.")
            return np.array(data).reshape((nrows, ncols))
        else:
            # vector
            if not value_str:
                return np.array([])
            data = list(map(float, value_str.split(',')))
            return np.array(data)

    # Handle pd.DataFrame
    if expected_type == "pd.DataFrame":
            # Expect something like: "iris=DATAFRAME:.grab_df_iris.csv"
            if not value_str.startswith("DATAFRAME:"):
                raise ValueError(
                    f"Expected 'DATAFRAME:' prefix, got {value_str} for type {expected_type}"
                )
            csv_path = value_str.split("DATAFRAME:", 1)[1]
            csv_path = csv_path.strip()
            # read the CSV with pandas
            df = pd.read_csv(csv_path)
            # remove that CSV file
            if os.path.exists(csv_path):
                os.remove(csv_path)
            return df

    raise ValueError(f"Unsupported type '{expected_type}' in @grab annotation.")
