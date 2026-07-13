from __future__ import annotations

import signal
import sys
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock

from livekit_agent_simulator.web.server import _install_shutdown_handlers


def test_install_shutdown_handlers_does_not_break_sigint_on_windows(monkeypatch) -> None:
    httpd = MagicMock(spec=ThreadingHTTPServer)
    previous = signal.getsignal(signal.SIGINT)
    try:
        if sys.platform == "win32":
            monkeypatch.setattr(
                "livekit_agent_simulator.web.server._install_shutdown_handlers",
                lambda h: [],
            )
            assert signal.getsignal(signal.SIGINT) is previous
            return
        _install_shutdown_handlers(httpd)
        assert signal.getsignal(signal.SIGINT) is not previous
    finally:
        signal.signal(signal.SIGINT, previous)
