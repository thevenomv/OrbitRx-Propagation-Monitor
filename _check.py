import py_compile, sys
try:
    py_compile.compile('app.py', doraise=True)
    print('Syntax OK')
except py_compile.PyCompileError as e:
    print(e)
