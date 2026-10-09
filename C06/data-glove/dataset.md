# GloVe 6B 50d subset (for the mathematics module's notebook)

- File: `glove6b-50d-subset.npz` (3,874,729 bytes), SHA-256 `da7efd39587326e233c16ffa8a8a89802f11de507bebaef1bb5b857d1f895f30`
- Contents: `words` (20,367 strings) and `vectors` (float32, 20,367 x 50): the 20,000 most frequent
  words of GloVe 6B (the file is ordered by frequency) plus the 367 other alphabetic words of the Larkfield
  ticket vocabulary that GloVe has. Load with `np.load(path)` (no pickle needed).
- Source: GloVe 6B, `glove.6B.50d.txt` from https://downloads.cs.stanford.edu/nlp/data/glove.6B.zip (SHA-256 of the text file `d8f717f8dd4b545cb7f418ef9f3d0c3e6e68a6f48b97d32f8b7aae40cb31f96f`),
  Wikipedia 2014 + Gigaword 5, 6 billion tokens, 400,000 uncased words. Made by `reference/c06/maths/s3d_glove_subset.py`.
- Licence: Open Data Commons Public Domain Dedication and License (PDDL) 1.0, as stated on
  https://nlp.stanford.edu/projects/glove/ ("This data is made available under the Public Domain Dedication and License v1.0").
  The subset is redistributed under the same terms.
- Attribution (asked for by the authors): Jeffrey Pennington, Richard Socher, and Christopher D. Manning. 2014.
  GloVe: Global Vectors for Word Representation. EMNLP 2014.
