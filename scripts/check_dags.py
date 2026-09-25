"""Import every DAG file, failing if any of them raises.

Airflow only reports a broken DAG after it has been deployed, as an "import error"
in the UI, so this runs the same import locally and in CI. It catches what
py_compile cannot: valid syntax that fails when executed, e.g. a name that does not
exist, a wrong import, or a callback that is called instead of passed.

Needs apache-airflow-task-sdk (see requirements-dev.txt), not a full Airflow install.
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
DAGS = ROOT / "dags"

# The DAG files do `from ingestion import ...`, which resolves from the project root.
# Running this script puts scripts/ on the path instead, so add the root explicitly.
sys.path.insert(0, str(ROOT))


def import_dag_files() -> int:
    failures = 0
    for path in sorted(DAGS.glob("*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            failures += 1
            print(f"FAIL {path}: cannot be loaded as a Python module")
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            failures += 1
            print(f"FAIL {path}: {type(e).__name__}: {e}")
        else:
            print(f"ok   {path}")
    return failures


if __name__ == "__main__":
    failed = import_dag_files()
    if failed:
        print(f"\n{failed} DAG file(s) failed to import")
    sys.exit(1 if failed else 0)
