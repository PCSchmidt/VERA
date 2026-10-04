"""Download the public datasets the Increment 2 loop's experiments use, with provenance (FND-C-02).

The sandbox has no network, so datasets are fetched here, on the host, into the git-ignored data/raw/datasets/ and
copied into a run's working directory. Each file gets a record in data/provenance.jsonl.

  airfoil_self_noise.dat  UCI Airfoil Self-Noise (1503 rows; 5 features, then the target), one of the TreeHFD
                          paper's real datasets (Table 2). Public, de-identified, UCI terms (CC BY 4.0).

  CaliforniaHousing/cal_housing.data
                          California Housing (Pace and Barry 1997; 20640 rows, 8 features then the target), the
                          credal-ambiguity-sets paper's Section 5.2 dataset, from the archive its README names.
                          Public, StatLib (no personal data).

Usage: uv run python scripts/fetch_datasets.py
"""

from __future__ import annotations

import io
import tarfile
import time
import zipfile
from pathlib import Path

import httpx

from vera.provenance import record

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "datasets"
DATASETS = {
    "airfoil_self_noise.dat": (
        "https://archive.ics.uci.edu/static/public/291/airfoil+self+noise.zip",
        "airfoil_self_noise.dat",
    ),
}


CALIFORNIA = (
    "https://s3.amazonaws.com/sagemaker-sample-files/datasets/tabular/california_housing/cal_housing.tgz",
    "CaliforniaHousing/cal_housing.data",
)


def fetch(url: str) -> bytes:
    for attempt in range(4):  # this machine has intermittent DNS failures
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=60)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (url, member) in DATASETS.items():
        dest = OUT / name
        if dest.exists():
            print(f"have {name}")
            continue
        with zipfile.ZipFile(io.BytesIO(fetch(url))) as z:
            dest.write_bytes(z.read(member))
        rec = record(ROOT, dest, url)
        print(f"fetched {name} sha256={rec['sha256'][:12]}…")
    url, member = CALIFORNIA
    dest = OUT / member
    if dest.exists():
        print(f"have {member}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(fetch(url)), mode="r:gz") as tar:
        dest.write_bytes(tar.extractfile(member).read())
    rec = record(ROOT, dest, url)
    print(f"fetched {member} sha256={rec['sha256'][:12]}…")


if __name__ == "__main__":
    main()
