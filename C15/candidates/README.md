# Candidate changes for the review practice

Six changes to `ticket-cleaner`, each as a patch for the `start` snapshot. Read them in the course's review lessons. Each one says where it comes from:

| Patch | Where it comes from | What the review finds |
|---|---|---|
| `good-bounded-request.patch` | **Real.** The recorded session `feature-bounded` (the task brief with acceptance criteria). | All 8 acceptance checks pass. `ruff format --check` asks to reformat 1 file: long lines. |
| `A-vague-request.patch` | **Real.** The recorded session `feature-vague` ("Add a way to filter the report by category."). | Its own tests pass, but 4 of 8 acceptance checks fail: one category only, exact spelling (`Billing` finds nothing), and a new `"category": null` key in **every** report. |
| `B-improve-while-there.patch` | **Real.** The recorded session `refactor-grows` (the brief, plus "improve the code wherever you can"). | Unrelated edits (a test reformatted, a type added to an unrelated function). One new test passes in a wide terminal and fails in an 80-column one: it depends on how `--help` wraps its lines. |
| `C-filter-before-summary.patch` | **Constructed** for the course. | Short and tidy, and all the tests pass. But it removes the other categories' tickets before the summary, so `valid_records` is 3 instead of 9 for `--category billing`. |
| `D-new-dependency.patch` | **Constructed** for the course. | Adds the package `Unidecode` to clean the names. The project does not need it, and its licence is the GPL. Do not install it to try the patch: the tests stop with an import error, and that is the point. |
| `E-clean-and-debug.patch` | **Constructed** for the course. **Do not use it in a folder that you want to keep.** | A `--clean` option deletes the folder of the output file. With `--output summary.json`, that folder is the project itself: in a copy made for the test, 44 files became 1. And a debug line prints every setting, the secret token too. |

To look at a patch in your editor, open it: it is a text file. To try a real one on a copy of `start` (in a Git repository):

```sh
git apply ../nextia-learning-labs/C15/candidates/A-vague-request.patch
git diff --stat
python -m pytest
git restore . && git clean -fd     # back to start
```
