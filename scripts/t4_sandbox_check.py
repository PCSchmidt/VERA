"""T4 measurement: local Docker as the sandbox for generated code (docs/04 T4).

Re-runnable evidence, not the sandbox module (that is `vera/sandbox/`). Needs the image from
docker/sandbox-treehfd/Dockerfile. Usage: uv run python scripts/t4_sandbox_check.py
"""
# ruff: noqa: E501, B007  (a measurement script: long one-line probes are the point)

import subprocess
import time
import uuid
from pathlib import Path

IMAGE = "vera-sandbox-treehfd:dd02152"
WORK = Path(__file__).resolve().parents[1] / "tmp" / "t4_work"  # git-ignored scratch, mounted as /work
WORK.mkdir(parents=True, exist_ok=True)
HARDENED = ["--network", "none", "--read-only", "--tmpfs", "/tmp:rw,size=64m,noexec", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "128", "--memory", "1g", "--memory-swap", "1g",
            "--cpus", "2"]  # fmt: skip


def run(code: str, *, flags=None, timeout=60, name=None, env=None):
    name = name or f"t4-{uuid.uuid4().hex[:8]}"
    cmd = ["docker", "run", "--rm", "--name", name, *(HARDENED if flags is None else flags),
           "-v", f"{WORK}:/work", "-w", "/work"]  # fmt: skip
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    cmd += [IMAGE, "python", "-c", code]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip(), time.perf_counter() - t0, name
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", "", time.perf_counter() - t0, name


def show(label, res):
    rc, out, err, dt, _ = res
    print(f"[{label}] rc={rc} {dt:.1f}s | {(out or err)[-300:]!r}")


# 0. startup overhead
for i in range(3):
    show("startup", run("pass"))

# 1. network: hardened vs control
net = ("import socket\ntry:\n s=socket.create_connection(('1.1.1.1',53),timeout=4);print('CONNECTED')\n"
       "except Exception as e: print('blocked',type(e).__name__)\n"
       "try:\n print(socket.gethostbyname('pypi.org'))\nexcept Exception as e: print('dns blocked',type(e).__name__)")
show("network none", run(net))
show("network CONTROL (default bridge)", run(net, flags=[]))

# 2. host files: only /work visible; no repo .env; no host drive mounts
probe = ("import os\nprint('work:',sorted(os.listdir('/work')))\n"
         "for p in ['/work/../.env','/mnt','/mnt/host','/c','/Users','/proc/1/environ']:\n"
         " print(p, os.path.exists(p), (os.listdir(p)[:4] if os.path.isdir(p) else ''))\n"
         "print([l.split()[1] for l in open('/proc/mounts') if '/work' in l or 'host' in l or '/mnt' in l])")
show("host files", run(probe))

# 3. writes: outside /work blocked, /work and /tmp allowed
w = ("for p in ['/etc/x','/opt/x','/home/sandbox/x','/usr/x','/work/ok.txt','/tmp/ok.txt']:\n"
     " try: open(p,'w').write('x'); print(p,'WROTE')\n except Exception as e: print(p,type(e).__name__)")
show("writes", run(w))
print("  host sees work/ok.txt:", (WORK / "ok.txt").exists())

# 4. wall-clock kill: the container itself must die, not just the docker CLI
name = f"t4-wall-{uuid.uuid4().hex[:6]}"
t0 = time.perf_counter()
p = subprocess.Popen(["docker", "run", "--rm", "--name", name, *HARDENED, IMAGE, "python", "-c", "while True: pass"])
try:
    p.wait(timeout=8)
except subprocess.TimeoutExpired:
    subprocess.run(["docker", "kill", name], capture_output=True)
    p.wait(timeout=30)
alive = subprocess.run(["docker", "ps", "-q", "--filter", f"name={name}"], capture_output=True, text=True).stdout.strip()
print(f"[wall kill] stopped after {time.perf_counter() - t0:.1f}s, container still running: {bool(alive)}")

# 5. memory limit
show("memory 1g, alloc 4g", run("x=bytearray(4*1024**3); x[::4096]=b'1'*len(x[::4096]); print('ALLOCATED')"))

# 6. process limit (fork bomb)
show("pids 128", run("import os\nn=0\ntry:\n while True:\n  os.fork() if os.fork()==0 else None\nexcept OSError as e: print('fork blocked',e)", timeout=40))

# 7. environment and identity
show("env keys", run("import os;print([k for k in os.environ if any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASS'))], os.getuid())"))

# 8. the unmodified baseline path: TreeHFD on the example's simulated data, subset size, metric printed
base = r"""
import numpy as np, xgboost as xgb, time
from numpy.random import default_rng
from treehfd import XGBTreeHFD
t0=time.time(); rng=default_rng(0); D=6; N=5000
cov=np.full((D,D),0.5); np.fill_diagonal(cov,1.0)
X=rng.multivariate_normal(np.zeros(D),cov,size=N); y=np.sin(2*np.pi*X[:,0])+X[:,0]*X[:,1]+X[:,2]*X[:,3]+rng.normal(0,.5,N)
m=xgb.XGBRegressor(eta=0.1,n_estimators=100,max_depth=6,n_jobs=2).fit(X,y)
Xn=rng.multivariate_normal(np.zeros(D),cov,size=N)
h=XGBTreeHFD(m); h.fit(X,interaction_order=2)
ym,y2=h.predict(Xn); pred=m.predict(Xn); hp=h.eta0+ym.sum(1)+y2.sum(1)
print('residual_rel_var=%.4f'%(np.var(pred-hp)/np.var(pred)),'seconds=%.1f'%(time.time()-t0))
open('/work/baseline.txt','w').write('done')
"""
show("TreeHFD baseline (n=5000, 100 trees)", run(base, timeout=300))
print("leftover t4 containers:", subprocess.run(["docker", "ps", "-aq", "--filter", "name=t4-"],
                                                 capture_output=True, text=True).stdout.split())
