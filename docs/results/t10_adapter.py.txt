import os
import re
import glob
import importlib.util
import subprocess

import pandas as pd

METHODS = ["lv", "cvar", "wass", "ridge", "erm"]
METRICS = ["mae", "rmse", "p98_abs_error", "cvar_abs_error"]
SCALE = 1e4
TIME_KEYS = ("val_time", "validation_time", "solve_time", "likelihood_time")


def _sh(cmd, env):
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("command failed: %s\n%s\n%s"
                           % (" ".join(cmd), r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout


def _norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def _match_method(value, meth):
    v = _norm(value)
    if meth == "lv":
        return v == "lv" or v.startswith("lv") or "credal" in v
    return meth in v


def _metric_col(cols, k):
    for c in cols:
        if _norm(c) == _norm(k):
            return c
    for c in cols:
        cl = c.lower()
        if k in cl and "time" not in cl:
            return c
    return None


def _pkg_files():
    spec = importlib.util.find_spec("credal_dro")
    if spec is None:
        raise RuntimeError("credal_dro not installed")
    dirs = list(spec.submodule_search_locations or [])
    files = []
    for d in dirs:
        for root, _, fs in os.walk(d):
            files += [os.path.join(root, f) for f in fs if f.endswith(".py")]
    return files


def _patch_settings(n):
    """Set replication count (and paper gap 0.30) wherever the parent defines them.
    Returns {path: original_text} for restoration."""
    rep_re = re.compile(r"^([ \t]*CALIFORNIA_HOUSING_NUM_REPLICATIONS\b[ \t]*(?::[^=\n]+)?=[ \t]*)[^\n#]+",
                        re.M)
    gap_re = re.compile(r"^([ \t]*CALIFORNIA_HOUSING_GAP_RATIO\b[ \t]*(?::[^=\n]+)?=[ \t]*)[^\n#]+",
                        re.M)
    origs = {}
    hits = []
    for p in _pkg_files():
        try:
            with open(p) as f:
                txt = f.read()
        except Exception:
            continue
        if "NUM_REPLICATIONS" in txt:
            for i, line in enumerate(txt.splitlines()):
                if "NUM_REPLICATIONS" in line:
                    hits.append("%s:%d: %s" % (p, i + 1, line.strip()))
        new, k = rep_re.subn(r"\g<1>%d" % n, txt)
        if k:
            new = gap_re.sub(r"\g<1>0.30", new)
            origs[p] = txt
            with open(p, "w") as f:
                f.write(new)
    if not origs:
        raise RuntimeError("no CALIFORNIA_HOUSING_NUM_REPLICATIONS definition found in credal_dro; "
                           "related lines:\n" + "\n".join(hits[:40]))
    return origs


def run(data_dir: str, work_dir: str, n_replications: int) -> dict:
    os.makedirs(work_dir, exist_ok=True)
    env = dict(os.environ)
    env["CALIFORNIA_HOUSING_DATASET_DIR"] = data_dir
    agg = os.path.join(work_dir, "agg")
    runs = os.path.join(work_dir, "runs")
    os.makedirs(agg, exist_ok=True)
    os.makedirs(runs, exist_ok=True)
    exe = "credaldro"

    origs = _patch_settings(n_replications)
    try:
        _sh([exe, "setup-lv", "lv_california_housing_val", agg, "--overwrite",
             "--experiment-data-dir", runs], env)
        _sh([exe, "batch", agg, "0", "99999", "--experiment-data-dir", runs], env)
        _sh([exe, "csv", agg, "--experiment-data-dir", runs], env)
    finally:
        for p, txt in origs.items():
            with open(p, "w") as f:
                f.write(txt)

    csvs = sorted(glob.glob(os.path.join(runs, "**", "results.csv"), recursive=True))
    if not csvs:
        csvs = sorted(glob.glob(os.path.join(agg, "**", "*.csv"), recursive=True))
    if not csvs:
        raise RuntimeError("no results csv found under %s or %s" % (runs, agg))
    df = pd.read_csv(csvs[0])
    cols = list(df.columns)

    mcol = next((c for c in cols if _norm(c) in
                 ("method", "methods", "algorithm", "algo", "name", "model", "estimator")), None)
    if mcol is None:
        for c in cols:
            if df[c].dtype == object:
                vals = df[c].astype(str).unique()
                hits = sum(any(_match_method(v, m) for v in vals) for m in METHODS)
                if hits >= 3:
                    mcol = c
                    break
    repcol = next((c for c in cols if _norm(c) in
                   ("rep", "replication", "replicate", "seed", "uuid", "run", "runid", "trial")), None)

    out = {}
    for meth in METHODS:
        out[meth] = {}
        if mcol is not None:
            mask = df[mcol].map(lambda v: _match_method(v, meth))
            sub = df[mask]
            if repcol is not None and sub[repcol].nunique() > 1:
                sub = sub.drop_duplicates(subset=[repcol], keep="first")
            if len(sub) == 0:
                raise RuntimeError("no rows for method %s; %s values: %s; columns: %s"
                                   % (meth, mcol, list(df[mcol].astype(str).unique())[:30], cols))
            sub = sub.head(n_replications)
            for k in METRICS:
                c = _metric_col(cols, k)
                if c is None:
                    raise RuntimeError("missing column for %s; columns: %s" % (k, cols))
                out[meth][k] = (sub[c].astype(float) / SCALE).tolist()
            tcols = [c for c in cols if any(t in c.lower() for t in TIME_KEYS)]
            if not tcols:
                raise RuntimeError("no timing columns; columns: %s" % cols)
            out[meth]["runtime_s"] = sub[tcols].astype(float).sum(axis=1).tolist()
        else:
            sub = df.head(n_replications)
            for k in METRICS:
                cc = [c for c in cols if meth in _norm(c) and k in c.lower()]
                if not cc:
                    raise RuntimeError("missing column for %s %s; columns: %s" % (meth, k, cols))
                out[meth][k] = (sub[cc[0]].astype(float) / SCALE).tolist()
            tc = [c for c in cols if meth in _norm(c) and any(t in c.lower() for t in TIME_KEYS)]
            if not tc:
                raise RuntimeError("no timing columns for %s; columns: %s" % (meth, cols))
            out[meth]["runtime_s"] = sub[tc].astype(float).sum(axis=1).tolist()
        for k, v in out[meth].items():
            if len(v) != n_replications:
                raise RuntimeError("expected %d replications for %s/%s, got %d (csv: %s, rows: %d)"
                                   % (n_replications, meth, k, len(v), csvs[0], len(df)))
    return out
