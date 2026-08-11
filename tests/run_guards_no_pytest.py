"""Minimal runner so the guards execute without pytest installed."""
import sys, traceback, importlib
sys.path.insert(0, ".")
import numpy as np
MODULE = sys.argv[1] if len(sys.argv) > 1 else "src.modeles.france_ze2020.herald76_dynamic_graph"
GUARDS = sys.argv[2] if len(sys.argv) > 2 else "tests/test_herald76_guards.py"
try:
    mod = importlib.import_module(MODULE)
except ModuleNotFoundError as e:
    print(f"implementacao ausente: {e}"); sys.exit(2)
sys.modules["pytest"] = type(sys)("pytest")
sys.modules["pytest"].importorskip = lambda *a, **k: mod
spec = importlib.util.spec_from_file_location("guards", GUARDS)
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
tests = [n for n in dir(g) if n.startswith("test_")]
fails = 0
for name in sorted(tests):
    try:
        getattr(g, name)()
        print(f"PASS  {name}")
    except Exception as e:
        fails += 1
        print(f"FAIL  {name}\n      {type(e).__name__}: {str(e)[:220]}")
print(f"\n{len(tests)-fails}/{len(tests)} passaram")
sys.exit(1 if fails else 0)
