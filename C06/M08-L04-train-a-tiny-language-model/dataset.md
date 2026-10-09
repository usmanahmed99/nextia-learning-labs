# Dataset card: Six Shakespeare tragedies (plain text)

Used by: C06-M08-L04 Train a tiny language model, `train-a-tiny-language-model.ipynb` and `train-a-tiny-language-model-solution.ipynb`

| Field | Value |
|---|---|
| Source | Project Gutenberg eBook #100, *The Complete Works of William Shakespeare*: <https://www.gutenberg.org/ebooks/100> (file <https://www.gutenberg.org/cache/epub/100/pg100.txt>) |
| Publisher / creator | William Shakespeare (1564–1616); digital text by Project Gutenberg (release January 1, 1994, "Most recently updated: August 24, 2025") |
| Licence | Public domain in the USA (works published before 1931). Shakespeare's plays are also public domain in other countries, but the copyright law of the country where you are also applies: check it. The Project Gutenberg licence and trademark text were removed, as its section 1.C allows for works that are not protected by copyright in the USA. |
| Attribution text | "Six tragedies by William Shakespeare, from Project Gutenberg eBook #100 (The Complete Works of William Shakespeare), public domain in the USA." Attribution is not required for public-domain text; we give it so others can find the source. |
| Version or access date | Downloaded 2026-10-08; source file SHA-256 `3cf4b3d44ee14cff4e14e78e2ad3318eff76f3f7f2afc3cee6bb925879110a37` (5,638,480 bytes) |
| File used | `shakespeare_tragedies.txt`, kept next to the notebook: yes (public domain) |
| SHA-256 | `59bd62e67e9720ca07b12d371b0311c858a0198c4a27466b382d3697daac94b4` |
| Size | 850,875 characters (862,599 bytes, UTF-8), 33,143 lines, 75 different characters |

## What one row means

There are no rows: the data is one continuous text. The model reads windows of 64 characters, and the target at every position is the next character of the same text.

## Why this dataset

A play has a shape that anyone sees at once: a speaker's name in capitals with a full stop on its own line, then short lines of verse. A character-level model learns that shape early in training and the spelling later, so samples at several steps show learning clearly. Compared with *Pride and Prejudice* (#1342: an illustrated 1894 edition that needs cleaning, and long paragraphs that hide the shape), *The Adventures of Sherlock Holmes* (#1661: public-domain status differs between countries, because Doyle died in 1930), *Grimms' Fairy Tales* (#2591: a mixed translation) and the popular "tiny-shakespeare" file (undocumented source and changes), this text is clean, public domain everywhere, and fully documented. Full comparison: `reference/c06/m08/l04/DATASET-RESEARCH.md` in the site repository.

## Changes we made

Kept only six plays, in the order of the Complete Works: *Hamlet*, *Julius Caesar*, *King Lear*, *Macbeth*, *Othello* and *Romeo and Juliet*. Removed everything before the first play and after the last one (the Project Gutenberg header, the table of contents of the Complete Works, the other works, the footer and the licence), so no reference to Project Gutenberg remains in the file. Line endings are `\n`; the plays are joined by three empty lines. Nothing inside a play was changed (spelling, curly quotes, stage directions such as `[_Exit._]` stay as they are). Script: `reference/c06/m08/l04/prepare_corpus.py`.

## Limitations and cautions

- One author, one genre, about 400 years old: a model trained on it writes pseudo-Elizabethan English and nothing else. It knows no facts about the world.
- Project Gutenberg does not name the printed edition behind this digital text, so spelling and punctuation follow that unnamed edition, not a modern scholarly one.
- The validation set is the last 10% of the text (the second half of *Romeo and Juliet*), so it shares names and style with the training text. It measures "more of the same plays", not "any English".
- The plays contain violence, death and the language of their time, including some insults that are offensive today. Generated text can recombine them.
