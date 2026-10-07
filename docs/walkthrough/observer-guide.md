# Running the walkthrough (for Chris, or whoever observes)

The gate `newuser_walkthrough` wants a person other than the builder to do the whole of S4 through the app, with their own key, while
someone writes down what happens. Everything the gate checks is in `tools/checks/check_newuser.py`.

**Before.** Give the person: the repository link, `participant-guide.md`, and an OpenRouter key with a small credit (a few dollars at
most) that you will switch off afterwards. Do not show them the app, the README's text or the examples first. Pick a machine state and
write it down (a fresh clone is best; their own laptop is better still, since it tests the install). Note the time they start.

**During.** Say nothing that helps. If they ask a question, say "what would you do if I weren't here?" and write the question down. If
they are stuck for more than about five minutes, write down where, then show them the next step and mark that confusion
`observer_helped: true`. Write down: each pause or wrong turn (`at`, `where`, `what` in their words), the time the first run was started,
and the time it finished.

**After.** Ask the four questions in the guide and write their answers down in their words. Then:

1. Copy `data/walkthrough/record.template.json` to `record.json` and fill it in. `coached` is true only if you helped throughout; a coached
   session is not a walkthrough and the check refuses it.
2. `uv run python scripts/collect_walkthrough_run.py <run_id>` copies the run's evidence (review, audit, ledger; never the key).
3. Switch off the person's key.
4. `bash scripts/gate-newuser.sh` should pass. Then you approve the gate yourself:
   `bash scripts/gate-engine.sh mark-passed newuser_walkthrough --approve "NEW USER WALKTHROUGH"`.

**State it honestly.** `independent_of_builder` is true only for someone who has not seen the repository or built any of it. If the only
person available is you, from a fresh clone, record `false`; the review will say it is a weaker test.
