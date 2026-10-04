# Provenance of the labels on the 10 real loop ideas (2026-10-04)

`helper_labels.csv` holds ten `distinct` labels, with a row-by-row rationale, produced by a language-model assistant working from the
sheet (the rationale says it applied "the abstract-only standard you gave"). Chris was asked which of three things they were and
answered, in his words: **"A model produced these and I adopt them after checking each."**

So they are recorded as **model-produced labels that Chris checked and adopted**: not a blind, independent human labelling. They
are reported under the `helper` key (not `chris`), and the review says this. They do not count as a second, independent labeller of
the judge's calls. All ten labels are the same value (`distinct`), so they cannot show the judge's `not distinct` calls (r-03 and
r-04 in the dev run) to be right or wrong, only that it agreed on the other eight.

If Chris later labels the rows himself without the model's rationale, those go in `chris_labels.csv` and are reported separately.
