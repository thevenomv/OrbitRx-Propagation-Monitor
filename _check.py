import py_compile
import pathlib
import sys

errors = []
for path in pathlib.Path(".").rglob("*.py"):
    if "build" in path.parts or "dist" in path.parts:
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("Syntax OK")
