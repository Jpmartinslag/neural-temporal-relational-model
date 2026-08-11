"""Minimal runner so the guards execute without pytest installed."""
import sys, traceback, importlib
sys.path.insert(0, ".")
import numpy as np
mod = importlib.import_module("src.modeles.france_ze2020.herald75_dynamic_graph")
sys.modules["pytest"] = type(sys)("pytest")
sys.modules["pytest"].importorskip = lambda *a, **k: mod
spec = importlib.util.spec_from_file_location("guards", "tests/test_herald75_guards.py")
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
