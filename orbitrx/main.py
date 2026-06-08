from __future__ import annotations


def main() -> None:
    import sys
    from orbitrx import __version__

    print(f"OrbitRx Propagation Monitor v{__version__}", flush=True)
    print(f"Python: {sys.executable}", flush=True)
    print(f"CWD: {__import__('os').getcwd()}", flush=True)

    try:
        from orbitrx.ui.qt_app import QT_AVAILABLE, run_qt_app
        if QT_AVAILABLE:
            print("UI: PySide6 (Qt) — v5 map with zoom/pan and layer toggles")
            run_qt_app()
            return
        print("UI: PySide6 import OK but QT_AVAILABLE=False")
    except ImportError as e:
        print(f"UI: PySide6 unavailable ({e}) — falling back to Tkinter")

    print("UI: Tkinter fallback (older map)")
    from orbitrx.ui.tk_app import TkOrbitRxApplication
    TkOrbitRxApplication().run()


if __name__ == "__main__":
    main()
