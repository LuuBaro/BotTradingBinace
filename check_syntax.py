import py_compile, sys
files = [
    'apps/api/phase4_routes.py',
    'apps/api/phase6_routes.py',
    'packages/shared/ai_orchestrator.py',
    'apps/worker/main.py',
]
ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'ERROR: {f} -> {e}')
        ok = False
sys.exit(0 if ok else 1)
