# Decisions

The main choices behind the `--category` option and the fix for Grace's bug,
and the suggestions that we did not accept. Each one says how it was checked.

## 1. `--category` filters the selection, not the file

`selected`, `by_category` and `average_priority` count only the chosen
categories. `valid_records` and `rejected` still describe the whole file,
because Grace uses them to see how clean the export is.

- Checked by: `test_categories_do_not_change_the_whole_file_counts`
  (`tests/test_report.py`) and `test_report_for_some_categories`
  (`tests/test_cli.py`).
- Rejected: a candidate change (constructed for the course's review practice) that removed the other categories' tickets in
  `cli.py`, before the summary. Its own test passed, but `valid_records` was 3
  instead of 9 for `--category billing`.

## 2. The report without `--category` stays exactly the same

The `categories` key is added only when the option is used. Grace's
spreadsheet reads the report, so a new key in every report could break it.

- Checked by: `tests/test_baseline.py`, written before any change, and
  `test_categories_key_only_with_the_option`.
- Rejected: a recorded assistant's answer to the vague request "Add a way to filter the
  report by category". It added `"category": null` to every report, accepted
  only one category, and matched the name exactly (`Billing` found nothing).
  Its own tests passed.

## 3. Category names are cleaned in one place

`clean_category` (`ticket_cleaner/parsing.py`) cleans a category in the same
way as the status and the ID: no spaces around it, small letters. Then it
changes the web form's names to ours. `--category` uses the same function, so
`--category Sign-in` selects the login tickets.

- Grace's bug: `clean_category` looked up the alias in small letters but kept
  the original text for other names, so `LOGIN` and `login` were two
  categories. The fix is one line: clean the text first.
- Checked by: `test_capital_letters_do_not_make_a_new_category` (it fails on
  the code before the fix), `test_web_form_export_has_one_line_per_team` and
  `test_web_form_names_work_in_the_category_option`.

## 4. No new dependency

The standard library is enough to clean names. We did not add a package.

- Rejected: a candidate (constructed for the course's review practice) that used the `Unidecode` package. The project does not
  need it (the names are English), and its licence is the GPL, which does not
  fit this MIT project without a review. It was not installed.

## 5. Not done, on purpose

- No fuzzy matching of misspelt categories (`biling`). The report must not
  guess; a misspelt category shows as its own line, and Grace can see it.
- No warning when `--category` matches no ticket. Grace did not ask for it.
  It would be a separate task.
- No `--clean` option that deletes old reports. The version reviewed in the
  course (constructed) deleted the whole folder of the output file: with
  `--output summary.json`, that is the project folder.

## Still needs a human review

- The list of the web form's names (`CATEGORY_ALIASES`) must match the form.
  Grace's team owns the form.
- The tests use made-up data. A real export can have other spellings.
