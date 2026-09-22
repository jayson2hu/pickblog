import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("output", ["26 passed\n1 failed", b"26 passed\n", "  ok " * 26])
def test_e2e_timeout_never_becomes_success(monkeypatch, output):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("l3_verify_test", scripts / "l3_verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = Mock()
    monkeypatch.setattr(module.subprocess, "Popen", Mock(return_value=server))
    monkeypatch.setattr(module, "npm_args", lambda *args: ["npm", *args])
    monkeypatch.setattr(module, "wait_for_reader_web", Mock())
    stop = Mock()
    monkeypatch.setattr(module, "stop_process_tree", stop)
    monkeypatch.setattr(module, "write_output", Mock())
    monkeypatch.setattr(
        module.subprocess, "run",
        Mock(side_effect=subprocess.TimeoutExpired("playwright", 240, output=output)),
    )
    with pytest.raises(subprocess.TimeoutExpired):
        module.run_reader_web_e2e()
    stop.assert_called_once_with(server)
