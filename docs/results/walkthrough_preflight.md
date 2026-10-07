# Walkthrough pre-flight: a clean clone, the README only (2026-10-07)

Done by the builder's assistant before the walkthrough, so that the person's time is not spent on defects a script can find. This is **not** the
walkthrough and is not evidence for MOE-4: the person who does it must be someone else, or the builder from a clean clone, recorded as such.

Setup: `git clone` of the pushed `main` into an empty folder (no `.env`, no cache, the provider keys removed from the environment), `uv sync`
(8 seconds), `uv run vera-app` on a spare port, then only the app's own screens' API.

| Check | Result |
|---|---|
| Clone and `uv sync` | 2 s and 8 s, no errors |
| First start | **Slower than 8 s** the first time (Python preparing files); nothing was wrong. The README now says it can take up to half a minute. |
| `/api/config` | `key_source: none`, no extra search keys: a fresh clone sees no key |
| Landing facts, example papers, example figures | all served from committed files (4 examples) |
| Starting a run with no key | refused in plain words, nothing created |
| A mistyped key | refused by OpenRouter's key check, not stored |
| The maintainer's TEST key pasted into the box | accepted |
| A full literature run (`rehearsal-1`, topic: conformal prediction under distribution shift, cap $0.50) | question proposed and confirmed, **7.5 minutes, $0.135, audit green** |

Not covered: the browser screens driven by a person (that is the walkthrough), Docker or GROBID absent (GROBID was running here), a non-Windows machine.
