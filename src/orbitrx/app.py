"""Application entry point."""

from __future__ import annotations

from orbitrx.models.context import AppContext
from orbitrx.ui.main_window import build_ui


def main() -> None:
    ctx = AppContext()
    build_ui(ctx)
    ctx.ui.window.mainloop()


if __name__ == "__main__":
    main()
