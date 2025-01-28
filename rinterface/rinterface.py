import subprocess
import re
import os
import numpy as np
from typing import Any


def rinterface(code: str, save: bool = False, fname: str = None,
               capture: bool = False, grab: bool = False):
    """
    Run R code in the terminal using Rscript, with optional:
      - saving of the R code to a file
      - capturing the entire script output
      - extracting variables via @grab annotations

    Parameters
    ----------
    code : str
        The R code to be executed.
    save : bool, optional
        Whether to save the R code to a file. Default is False.
    fname : str, optional
        The filename to save the R code if save is True. Default is None.
    capture : bool, optional
        Whether to capture the stdout/stderr of the R script. Default is False.
    grab : bool, optional
        Whether to extract specific variables using the # @grab{type} syntax. Default is False.

    Returns
    -------
    Any or subprocess.CompletedProcess or None
        - If `grab=True`, returns the extracted variable(s) in Python form.
        - If `capture=True` and `grab=False`, returns the CompletedProcess object
          (so you can see stdout/stderr).
        - Otherwise returns None.
    """
    temp_file = ".temp.R"
    temp_output = ".grab_output.txt"
    annotated_lines = []
    if grab:
        annotated_lines = re.findall(r"#\s*@grab\{([^}]+)\}\n(.+)", code)
    grab_snippet = ""
    for var_type, var_def in annotated_lines:
        snippet = f"""
cat("{var_def}=", file="{temp_output}", append=TRUE)
if (is.matrix({var_def})) {{
  dims <- dim({var_def})
  cat(paste0(paste(dims, collapse="x"), ":"), file="{temp_output}", append=TRUE)
  cat(paste({var_def}, collapse=","), file="{temp_output}", append=TRUE)
  cat("\\n", file="{temp_output}", append=TRUE)
}} else if (is.vector({var_def})) {{
  cat(paste({var_def}, collapse=","), file="{temp_output}", append=TRUE)
  cat("\\n", file="{temp_output}", append=TRUE)
}} else {{
  # fallback for scalar, string, etc.
  cat(as.character({var_def}), file="{temp_output}", append=TRUE)
  cat("\\n", file="{temp_output}", append=TRUE)
}}
"""
        grab_snippet += snippet

    # If we have # @grab{...}, append the code to do the file-writing
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
            # Capture stdout/stderr in a CompletedProcess
            results = subprocess.run(
                ["Rscript", temp_file],
                text=True,
                capture_output=True,
                check=True
            )
        else:
            # No capturing, but still raise on errors
            results = subprocess.run(
                ["Rscript", temp_file],
                text=True,
                check=True,
                capture_output=True  # So we can show errors if any
            )

        # If user only wants the captured output (and not grabbing variables)
        if grab is False and capture is True:
            return results  # a CompletedProcess object

        # If we are not grabbing variables, just return None
        if grab is False:
            return None

        # At this point, we *are* grabbing variables
        # Read all lines from .grab_output.txt
        if not os.path.exists(temp_output):
            # Means R might have crashed or no variables were actually written
            return None

        with open(temp_output, "r") as f:
            grabbed_lines = f.readlines()

        # Parse each line with parse_r_output, using the declared type
        parsed_results = []
        for (var_type, var_def), line in zip(annotated_lines, grabbed_lines):
            parsed_results.append(parse_r_output(line.strip(), var_type))

        # Return single item or tuple
        if len(parsed_results) == 1:
            return parsed_results[0]
        return tuple(parsed_results)

    except subprocess.CalledProcessError as e:
        # Show the real error from R (stderr) for debugging
        msg = f"R script execution failed: Exit code={e.returncode}\n"
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

    For matrices, we expect a format like:
        M=2x3:1,2,3,4,5,6
    For vectors:
        M=1,2,3,4
    For scalars/strings:
        M=123  or  M=hello

    Parameters
    ----------
    line : str
        The output line, e.g. 'M=2x3:1,2,3,4,5,6'.
    expected_type : str
        One of ['float', 'int', 'str', 'np.ndarray', 'list[int]', 'list[float]', 'list[str]'].

    Returns
    -------
    The parsed Python object.
    """
    # Split on the first '=' to get the variable name and the data string
    if '=' not in line:
        # If something is malformed
        raise ValueError(f"Cannot parse line (no '=' found): {line}")

    var_name, value_str = line.split('=', 1)
    value_str = value_str.strip()

    # Basic types
    if expected_type == "float":
        return float(value_str)
    if expected_type == "int":
        return int(value_str)
    if expected_type == "str":
        return value_str

    # If it's a list[...] type
    if expected_type.startswith("list["):
        subtype = expected_type[5:-1].strip()  # e.g. "int", "float", "str"
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
            raise ValueError(f"Unsupported list element type '{subtype}'.")

    # If it's "np.ndarray", we expect shape info or a vector
    if expected_type == "np.ndarray":
        # If there's a 'ROWSxCOLS:' prefix, parse it
        if ':' in value_str and 'x' in value_str:
            shape_part, array_part = value_str.split(':', 1)
            rows_cols = shape_part.split('x')
            if len(rows_cols) != 2:
                raise ValueError(f"Invalid matrix shape '{shape_part}' in line: {line}")
            nrows, ncols = map(int, rows_cols)
            data = list(map(float, array_part.split(','))) if array_part.strip() else []
            if len(data) != nrows * ncols:
                raise ValueError("Number of values does not match matrix shape.")
            return np.array(data).reshape((nrows, ncols))
        else:
            # Possibly just a vector
            if not value_str:
                return np.array([])
            data = list(map(float, value_str.split(',')))
            return np.array(data)

    # If none of the above matched, raise an error
    raise ValueError(f"Unsupported type '{expected_type}' in @grab annotation.")
