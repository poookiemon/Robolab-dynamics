"""UI event controllers and background thread dispatchers."""

import threading
from typing import Callable, Any


def run_in_background(task: Callable[..., Any], *args, on_complete: Callable[[Any], None] = None, **kwargs) -> threading.Thread:
    """Run a long-running task in a daemon background thread without freezing the UI."""
    def worker():
        res = task(*args, **kwargs)
        if on_complete:
            on_complete(res)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
