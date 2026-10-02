"""TreeHFD baseline smoke run: the README's simulated-data example without plotting.

Prints the metric the loop optimises (relative variance of the XGBoost-minus-HFD residual) and the wall time.
Runs inside the sandbox image (docker/sandbox-treehfd/Dockerfile); used by tests/test_sandbox.py.
"""

import time

import numpy as np
import xgboost as xgb
from numpy.random import default_rng
from treehfd import XGBTreeHFD

t0 = time.time()
rng = default_rng(0)
D, N = 6, 5000
cov = np.full((D, D), 0.5)
np.fill_diagonal(cov, 1.0)
X = rng.multivariate_normal(np.zeros(D), cov, size=N)
y = np.sin(2 * np.pi * X[:, 0]) + X[:, 0] * X[:, 1] + X[:, 2] * X[:, 3] + rng.normal(0, 0.5, N)
model = xgb.XGBRegressor(eta=0.1, n_estimators=100, max_depth=6, n_jobs=2).fit(X, y)
X_new = rng.multivariate_normal(np.zeros(D), cov, size=N)
hfd = XGBTreeHFD(model)
hfd.fit(X, interaction_order=2)
y_main, y_order2 = hfd.predict(X_new)
pred = model.predict(X_new)
hfd_pred = hfd.eta0 + y_main.sum(1) + y_order2.sum(1)
print(f"residual_rel_var={np.var(pred - hfd_pred) / np.var(pred):.4f} seconds={time.time() - t0:.1f}")
