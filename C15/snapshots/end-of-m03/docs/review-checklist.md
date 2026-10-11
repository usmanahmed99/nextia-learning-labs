# Review checklist for a generated change

Use it for every diff, from an assistant or from a person. Read the whole diff
first, then go through the list. Write down each finding with its file and line.

## Scope

- [ ] Every changed file is one that the task names, or the change explains why.
- [ ] No unrelated edits: no renamed names, moved code, new formatting or
      "improvements" that the task did not ask for.
- [ ] No file is deleted, and no data file is changed.

## Behaviour and contracts

- [ ] Each acceptance criterion has a line of code and a test that checks it.
- [ ] The output that others read (the report's keys, the printed lines, the
      exit codes) is unchanged, unless the task changes it.
- [ ] Edge cases: an empty input, a name with capital letters or spaces, a
      value that no record has.
- [ ] The tests would fail without the change: they test behaviour, not the
      code's own words.

## Dependencies

- [ ] No new package, or: it exists on pypi.org, it is maintained, its licence
      fits the project (MIT), and the standard library cannot do the job.
- [ ] Every function or option that the change calls exists in the installed
      version.

## Security and data

- [ ] Input from a file, an argument or the network is checked before it is
      used as a path, a command or a number.
- [ ] No secret is printed, logged, saved or sent.
- [ ] Nothing is deleted or overwritten without the user asking for it.

## Checks that I ran myself

- [ ] `python -m pytest`
- [ ] `ruff check .` and `ruff format --check .`
- [ ] The commands of the task, with their expected results.
