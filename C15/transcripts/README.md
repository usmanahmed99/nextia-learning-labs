# Recorded assistant sessions

Each session is a real run of a coding assistant on a fresh copy of the `start` snapshot. Each `.md` file has the exact prompts, everything that the assistant printed, the diff after each turn and the result of the tests and checks. Each `.patch` file is the whole change of the session.

- **Assistant:** [Aider](https://aider.chat) 0.86.2, an open-source coding assistant that works in a terminal (Apache-2.0). It can read the files that you give it, see a map of the repository, change files and, if you allow it, run a test command. One session uses the "chat" mode instead: the task and the files are sent in one message, as when you paste code into a chat window.
- **Models:** `chat-strong` (a larger model) and `chat-small` (a smaller, cheaper one), on Azure. Each transcript names the model version.
- **Not changed:** nothing in a transcript is edited, except the folder paths. There is no key or password in them.
- A different run, another model or another assistant can give a different answer. Use the transcripts to practise the habits, not to predict what your assistant will do.

| Session | What it shows | The result |
|---|---|---|
| `feature-vague` | "Add a way to filter the report by category." | 4 files, +77 −3. Its tests pass, but only 4 of 8 acceptance checks; every report gets a new key. |
| `feature-bounded` | The same feature as a task brief with acceptance criteria | 5 files, +145 −4. All 8 acceptance checks pass. |
| `feature-bounded-small` | The same brief, with the smaller model | 5 files, +86 −3. All 8 acceptance checks pass. |
| `feature-chat-mode` | The same brief in chat mode | The reply's diff did not apply (`git apply`: corrupt patch). In chat mode, you move the code yourself. The reply's diff, unchanged, is in `feature-chat-mode.reply.diff`. |
| `feature-plan-first` | Ask for an explanation and a plan first, then step 1 only | Turn 1 changes no file; turn 2 does step 1: 2 files, +82 −4. |
| `bug-little-context` | "The categories in the report are wrong. Fix it." with one file and no repository map | No change: the assistant asked for an example and the expected result. |
| `bug-relevant-context` | Grace's report, a minimal input and the right files | 2 files, +20 −3. All 5 bug checks pass. |
| `bug-fix-blind` | "Grace says the report is wrong… Fix it." (repository map on) | Fixed in one turn, 3 files, +44 −3, without reproducing first. |
| `bug-fix-blind-small` | The same, with the smaller model | Fixed in one turn with a one-line change, and no test. |
| `bug-fix-blind-no-map` | The same, with two files and no map, and "It is still wrong. Fix it." | Two turns asked for evidence; the third guessed right, with no test. 3 turns, 5 model calls. |
| `bug-fix-evidence` | Hypothesis first, then a failing test, then the smallest fix | The test failed first (1 failed, 24 passed); the fix: 1 line. |
| `tests-mirror` | "Write tests for clean_category." | 11 new tests pass on the buggy code. 2 of them fail after the fix: they repeat the bug. |
| `tests-failing-first` | A test that must fail because of the bug | 1 test; it fails on the buggy code and passes after the fix. |
| `refactor-grows` | The feature brief + "improve the code wherever you can" | 5 files, +171 −10, with unrelated edits and a test that depends on the terminal width. |
| `refactor-open` | "Refactor the code in ticket_cleaner/ to make it cleaner…" | 3 files, +40 −21. The tests pass; Grace's bug is still there. |
| `deps-ask`, `deps-ask-small` | "Which pip packages should I install to normalize category names?" | Both models answered that no package is needed. |
