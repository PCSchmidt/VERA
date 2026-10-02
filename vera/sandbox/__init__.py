"""Sandbox for agent-written and third-party code (FND-F-03, docs/04 T4: local Docker).

`run_script` is the only place in VERA where generated code executes (`tools/checks/check_sandbox_use.py` forbids
`exec`, `eval`, `subprocess` and friends elsewhere under vera/). The container runs with no network, a read-only
root, no capabilities, CPU, memory and process limits, a small `/tmp`, and only the working directory mounted at
`/work`. The host environment is not inherited: nothing reaches the container unless it is passed in `env`, and
names that look like secrets are refused. The wall limit is enforced with `docker kill` by container name (killing
only the `docker` client would leave the container running), and is charged to the run's `Budget`, so experiment time
counts against `max_wall_seconds` the way model-call time does.

The image is built in advance from a pinned checkout (docker/sandbox-treehfd/Dockerfile); building needs the network
once, outside the sandbox. A run may be granted the network with a reason, which is recorded on the result.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from vera.schemas import Budget, BudgetExceeded

DEFAULT_IMAGE = "vera-sandbox-treehfd:dd02152"
SCRIPT_NAME = "_run.py"
_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", re.IGNORECASE)
_MAX_OUTPUT = 20_000  # characters of stdout/stderr kept on the result
KILL_MARGIN_SECONDS = 3  # `docker kill` + removal take a second or two; the budgeted wall limit leaves room for it


class SandboxUnavailable(RuntimeError):
    """Docker is not running, or the sandbox image has not been built."""


@dataclass(frozen=True)
class SandboxLimits:
    wall_seconds: int = 300
    memory_mb: int = 1024
    cpus: float = 2.0
    pids: int = 128
    tmp_mb: int = 64
    max_workdir_mb: float = 256.0  # `/work` has no quota; the size is checked after the run


@dataclass
class SandboxResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    oom_killed: bool
    wall_seconds: float
    workdir_mb: float
    workdir_over_limit: bool
    network_granted: bool
    network_reason: str | None
    container: str
    files: list[str] = field(default_factory=list)  # files in the working directory after the run

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not (self.timed_out or self.oom_killed or self.workdir_over_limit)


def _docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["docker", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            check=False,
        )  # fmt: skip
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise SandboxUnavailable(f"docker is not usable: {exc}") from exc


def check_available(image: str = DEFAULT_IMAGE) -> None:
    """Raise `SandboxUnavailable` unless the Docker daemon answers and the image exists."""
    if _docker("info", "--format", "{{.ServerVersion}}", timeout=30).returncode != 0:
        raise SandboxUnavailable("the Docker daemon is not running")
    if _docker("image", "inspect", image).returncode != 0:
        raise SandboxUnavailable(f"image {image!r} not found; build it from docker/sandbox-treehfd/Dockerfile")


def _dir_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1024**2


def _check_env(env: dict[str, str]) -> None:
    bad = [k for k in env if _SECRET_NAME.search(k)]
    if bad:
        raise ValueError(f"refusing to pass secret-looking variables into the sandbox: {sorted(bad)}")


def run_script(
    script: str | Path,
    workdir: Path,
    *,
    limits: SandboxLimits = SandboxLimits(),  # noqa: B008 - frozen dataclass
    image: str = DEFAULT_IMAGE,
    network: bool = False,
    network_reason: str | None = None,
    env: dict[str, str] | None = None,
    budget: Budget | None = None,
) -> SandboxResult:
    """Run Python source (or a script file) in the sandbox with `workdir` mounted at `/work`.

    `budget`: the wall limit is capped to the budget's remaining wall seconds less `KILL_MARGIN_SECONDS`, so a kill
    still lands inside the budget (`BudgetExceeded` if that leaves no time), and the time used is charged to it
    afterwards, without counting as a model call.
    """
    if network and not network_reason:
        raise ValueError("a network grant needs a reason, which is recorded on the result")
    _check_env(env or {})
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    wall = limits.wall_seconds
    if budget is not None:
        remaining = budget.max_wall_seconds - budget.elapsed_seconds
        if remaining <= KILL_MARGIN_SECONDS:
            raise BudgetExceeded(f"wall: {remaining}s left of {budget.max_wall_seconds}s, not enough to run and stop")
        wall = min(wall, remaining - KILL_MARGIN_SECONDS)
    check_available(image)

    source = Path(script).read_text(encoding="utf-8") if isinstance(script, Path) else script
    (workdir / SCRIPT_NAME).write_text(source, encoding="utf-8")

    name = f"vera-sbx-{uuid.uuid4().hex[:10]}"
    cmd = [
        "docker", "run", "--name", name, *(["--network", "bridge"] if network else ["--network", "none"]),
        "--read-only", "--tmpfs", f"/tmp:rw,size={limits.tmp_mb}m,noexec", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--pids-limit", str(limits.pids),
        "--memory", f"{limits.memory_mb}m", "--memory-swap", f"{limits.memory_mb}m", "--cpus", str(limits.cpus),
        "-v", f"{workdir}:/work", "-w", "/work",
    ]  # fmt: skip
    for key, value in (env or {}).items():
        cmd += ["-e", f"{key}={value}"]
    cmd += [image, "python", f"/work/{SCRIPT_NAME}"]

    start = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        )  # fmt: skip
        try:
            stdout, stderr = proc.communicate(timeout=wall)
        except subprocess.TimeoutExpired:
            timed_out = True
            _docker("kill", name, timeout=30)  # the container, not just the docker client
            stdout, stderr = proc.communicate(timeout=60)
        elapsed = time.perf_counter() - start
        inspect = _docker("inspect", "--format", "{{.State.OOMKilled}}", name)
        oom = inspect.stdout.strip() == "true"
    finally:
        _docker("rm", "-f", name, timeout=60)

    size_mb = _dir_mb(workdir)
    if budget is not None:
        used = min(math.ceil(elapsed), budget.max_wall_seconds - budget.elapsed_seconds)  # never past the limit
        budget.charge(0.0, seconds=used, calls=0)  # experiment time counts against the wall budget
    return SandboxResult(
        exit_code=None if timed_out else proc.returncode,
        stdout=stdout[-_MAX_OUTPUT:],
        stderr=stderr[-_MAX_OUTPUT:],
        timed_out=timed_out,
        oom_killed=oom,
        wall_seconds=elapsed,
        workdir_mb=size_mb,
        workdir_over_limit=size_mb > limits.max_workdir_mb,
        network_granted=network,
        network_reason=network_reason if network else None,
        container=name,
        files=sorted(p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_file()),
    )


def clear_workdir(workdir: Path) -> None:
    """Remove everything in a working directory (between attempts, or after a size violation)."""
    for child in Path(workdir).iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
