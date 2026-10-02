"""FND-F-03: generated code runs only in the sandbox, which isolates it. Real containers; needs Docker.

Skipped when Docker or the image is missing, unless VERA_REQUIRE_DOCKER=1 (the `sandbox_ready` gate sets it), in
which case a missing sandbox fails the tests instead of skipping them.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from vera.sandbox import SandboxLimits, SandboxUnavailable, check_available, run_script
from vera.schemas import Budget, BudgetExceeded

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tools" / "checks" / "check_sandbox_use.py"

try:
    check_available()
    AVAILABLE, WHY = True, ""
except SandboxUnavailable as exc:
    AVAILABLE, WHY = False, str(exc)

if not AVAILABLE and os.environ.get("VERA_REQUIRE_DOCKER") == "1":
    raise RuntimeError(f"VERA_REQUIRE_DOCKER=1 but the sandbox is unavailable: {WHY}")

needs_docker = pytest.mark.skipif(not AVAILABLE, reason=f"sandbox unavailable: {WHY}")


def load_check():
    sys.path.insert(0, str(CHECK.parent))  # the check imports its sibling _common
    spec = importlib.util.spec_from_file_location("check_sandbox_use", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def container_exists(name: str) -> bool:
    out = subprocess.run(["docker", "ps", "-aq", "--filter", f"name={name}"], capture_output=True, text=True)
    return bool(out.stdout.strip())


@needs_docker
def test_FND_F_03_no_network_by_default_and_a_grant_is_recorded(tmp_path: Path) -> None:
    probe = (
        "import socket\n"
        "try:\n socket.create_connection(('1.1.1.1', 53), timeout=4); print('CONNECTED')\n"
        "except OSError as e: print('blocked', type(e).__name__)\n"
        "try:\n socket.gethostbyname('pypi.org'); print('RESOLVED')\n"
        "except OSError as e: print('dns blocked', type(e).__name__)\n"
    )
    res = run_script(probe, tmp_path)
    assert res.ok and "CONNECTED" not in res.stdout and "RESOLVED" not in res.stdout
    assert "blocked" in res.stdout and "dns blocked" in res.stdout
    assert (res.network_granted, res.network_reason) == (False, None)

    with pytest.raises(ValueError, match="reason"):
        run_script(probe, tmp_path, network=True)  # a grant must say why
    granted = run_script(probe, tmp_path, network=True, network_reason="test: control run")
    assert "CONNECTED" in granted.stdout  # the test can fail: the same probe connects when granted
    assert (granted.network_granted, granted.network_reason) == (True, "test: control run")


@needs_docker
def test_FND_F_03_sees_only_its_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    monkeypatch.setenv("VERA_TEST_HOST_VALUE", "must-not-reach-the-container")
    probe = (
        "import os\n"
        "print('work', sorted(os.listdir('/work')))\n"
        "for p in ['/work/../.env', '/c', '/Users', '/mnt/host', '/host_mnt']:\n print('path', p, os.path.exists(p))\n"
        "print('env', [k for k in os.environ if 'VERA_TEST' in k])\n"
    )
    res = run_script(probe, tmp_path)
    assert res.ok, res.stderr
    assert "'data.csv'" in res.stdout and "env []" in res.stdout
    path_lines = [ln for ln in res.stdout.splitlines() if ln.startswith("path ")]
    assert len(path_lines) == 5 and all(ln.endswith("False") for ln in path_lines)


@needs_docker
def test_FND_F_03_writes_only_to_work_and_tmp(tmp_path: Path) -> None:
    probe = (
        "for p in ['/etc/x', '/opt/x', '/usr/x', '/home/sandbox/x', '/work/out.txt', '/tmp/t.txt']:\n"
        " try:\n  open(p, 'w').write('x'); print(p, 'WROTE')\n"
        " except OSError:\n  print(p, 'refused')\n"
    )
    res = run_script(probe, tmp_path)
    lines = dict(ln.split(" ", 1) for ln in res.stdout.splitlines())
    assert [lines[p] for p in ("/etc/x", "/opt/x", "/usr/x", "/home/sandbox/x")] == ["refused"] * 4
    assert lines["/work/out.txt"] == "WROTE" and lines["/tmp/t.txt"] == "WROTE"
    assert (tmp_path / "out.txt").read_text() == "x"  # the host sees /work files
    assert "out.txt" in res.files


@needs_docker
def test_FND_F_03_wall_limit_kills_the_container_itself(tmp_path: Path) -> None:
    res = run_script("while True: pass", tmp_path, limits=SandboxLimits(wall_seconds=5))
    assert res.timed_out and not res.ok and res.exit_code is None
    assert 4.5 <= res.wall_seconds < 30
    assert not container_exists(res.container)  # removed, not left running


@needs_docker
def test_FND_F_03_memory_and_process_limits(tmp_path: Path) -> None:
    mem = run_script(
        "x = bytearray(2 * 1024**3); x[::4096] = b'1' * len(x[::4096])",
        tmp_path,
        limits=SandboxLimits(memory_mb=256, wall_seconds=60),
    )
    assert mem.oom_killed and not mem.ok

    bomb = run_script(
        "import os\nn = 0\ntry:\n while True:\n  os.fork()\n  n += 1\nexcept OSError:\n print('blocked after', n)\n",
        tmp_path,
        limits=SandboxLimits(pids=32, wall_seconds=30),
    )
    assert "blocked after" in bomb.stdout or bomb.exit_code != 0


@needs_docker
def test_FND_F_03_no_secrets_reach_the_sandbox(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="secret"):
        run_script("pass", tmp_path, env={"OPENROUTER_API_KEY": "sk-or-x"})
    with pytest.raises(ValueError, match="secret"):
        run_script("pass", tmp_path, env={"my_token": "x"})
    names = "sorted(k for k in os.environ if any(s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET', 'PASS')))"
    res = run_script(f"import os; print({names})", tmp_path)
    assert "OPENROUTER" not in res.stdout and "OPENALEX" not in res.stdout
    assert re.fullmatch(r"\[('GPG_KEY')?\]", res.stdout.strip())  # only the base image's public GPG key id
    passed = run_script("import os; print(os.environ['VERA_PARAM'])", tmp_path, env={"VERA_PARAM": "7"})
    assert passed.stdout.strip() == "7"  # explicit, non-secret variables do pass


@needs_docker
def test_FND_F_03_working_directory_size_is_checked_after_the_run(tmp_path: Path) -> None:
    res = run_script(
        "open('/work/big.bin', 'wb').write(b'0' * (3 * 1024**2))", tmp_path, limits=SandboxLimits(max_workdir_mb=1.0)
    )
    assert res.exit_code == 0 and res.workdir_over_limit and not res.ok and res.workdir_mb > 2.9


@needs_docker
def test_FND_F_03_wall_time_is_capped_and_charged_to_the_budget(tmp_path: Path) -> None:
    budget = Budget(max_usd=1.0, max_wall_seconds=8, elapsed_seconds=2)
    res = run_script("while True: pass", tmp_path, limits=SandboxLimits(wall_seconds=600), budget=budget)
    assert res.timed_out and res.wall_seconds < 10  # capped to the 6 s left less the kill margin, not 600
    assert 4 <= budget.elapsed_seconds <= 8 and budget.model_calls_used == 0  # time charged, not a model call
    with pytest.raises(BudgetExceeded):  # nothing (or too little) left: refused before any container starts
        run_script("pass", tmp_path, budget=Budget(max_usd=1.0, max_wall_seconds=5, elapsed_seconds=5))
    with pytest.raises(BudgetExceeded):
        run_script("pass", tmp_path, budget=Budget(max_usd=1.0, max_wall_seconds=10, elapsed_seconds=8))


@needs_docker
def test_FND_F_03_treehfd_baseline_runs_in_the_sandbox(tmp_path: Path) -> None:
    script = ROOT / "docker" / "sandbox-treehfd" / "baseline_smoke.py"
    res = run_script(script, tmp_path, limits=SandboxLimits(wall_seconds=180))
    assert res.ok, res.stderr[-500:]
    m = re.search(r"residual_rel_var=([0-9.]+)", res.stdout)
    assert m and 0.0 < float(m.group(1)) < 0.05  # about 1%, as measured for T4


def test_FND_F_03_unavailable_sandbox_raises_instead_of_running_on_the_host(tmp_path: Path) -> None:
    with pytest.raises(SandboxUnavailable):
        run_script("open('ran_on_host', 'w')", tmp_path, image="vera-no-such-image:0")
    assert not (tmp_path / "ran_on_host").exists() and not (Path.cwd() / "ran_on_host").exists()


# ── the "only inside the sandbox" check ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source",
    [
        "exec('x=1')",
        "eval('1')",
        "import subprocess",
        "from subprocess import run",
        "import os\nos.system('ls')",
        "import os\nos.popen('ls')",
        "__import__('os')",
        "import importlib\nimportlib.import_module('x')",
        "import runpy",
        "compile('1', 'f', 'eval')",
        "import multiprocessing",
    ],
)
def test_FND_F_03_check_flags_host_side_execution(source: str) -> None:
    assert load_check().violations(source)


def test_FND_F_03_check_ignores_harmless_code() -> None:
    assert not load_check().violations("import json\nx = json.loads('1')\nprint(1)")


def test_FND_F_03_repository_passes_the_sandbox_use_check() -> None:
    out = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
