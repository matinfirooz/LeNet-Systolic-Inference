"""Execute this notebook cell-by-cell with IPython, preserving genuine outputs.

This headless route requires IPython and the plotting packages, but no running
Jupyter server. Opening the same file in Jupyter and choosing Run All is equivalent.
"""

import json
import os
import sys
from pathlib import Path
from time import perf_counter

from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output


def main():
    root = Path(__file__).resolve().parents[1]
    notebook_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "HW3_Matin_Firoozbakht.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    os.chdir(notebook_path.parent)
    os.environ["MPLBACKEND"] = "Agg"
    shell = InteractiveShell.instance()
    shell.ast_node_interactivity = "last_expr"
    started = perf_counter()
    count = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        count += 1
        code = "".join(cell["source"])
        print(f"Executing code cell {count}: {code.splitlines()[0][:100]}", flush=True)
        with capture_output(display=True) as captured:
            outcome = shell.run_cell(code, store_history=True, silent=False)
        outputs = []
        if captured.stdout:
            outputs.append({"output_type": "stream", "name": "stdout", "text": captured.stdout.splitlines(True)})
        if captured.stderr:
            outputs.append({"output_type": "stream", "name": "stderr", "text": captured.stderr.splitlines(True)})
        for output in captured.outputs:
            outputs.append({"output_type": "display_data", "data": output.data, "metadata": output.metadata})
        cell["outputs"], cell["execution_count"] = outputs, count
        if outcome.error_before_exec or outcome.error_in_exec:
            notebook_path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            print(captured.stdout, file=sys.stderr)
            print(captured.stderr, file=sys.stderr)
            raise RuntimeError(f"Notebook code cell {count} failed") from (outcome.error_before_exec or outcome.error_in_exec)
    assert len({cell["id"] for cell in notebook["cells"]}) == len(notebook["cells"])
    notebook_path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Executed {count} code cells successfully in {perf_counter() - started:.1f} seconds.")
    print(f"Saved: {notebook_path.name}")


if __name__ == "__main__":
    main()
