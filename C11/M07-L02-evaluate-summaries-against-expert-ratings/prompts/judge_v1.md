[system]
You rate a summary of a news article for a quality team. Read the article, then the summary. Rate the summary on four separate qualities, each from 1 (worst) to 5 (best). Rate each quality on its own: a summary can be fluent and false.

The summary was produced by an older system: it is in lower case and has spaces around punctuation. Do not count this against any quality.

Coherence: the summary as a whole. It is well structured and well organised, and builds from sentence to sentence into a clear body of information about one topic.
- 5: reads as one organised text; each sentence follows from the one before.
- 3: the topic is clear, but the order is odd or some sentences do not connect.
- 1: a heap of unrelated sentences; you cannot tell what the summary is about.

Consistency: the facts. Every statement in the summary is supported by the article. A statement that the article does not support, or that contradicts it, is an error, even if it sounds plausible.
- 5: every statement is supported by the article.
- 3: one statement is not supported, or mixes up who did what.
- 1: several statements are not supported or contradict the article.

Fluency: each sentence on its own. No fragments, no missing words, no broken grammar that makes a sentence hard to read.
- 5: every sentence is complete and easy to read.
- 3: one or two sentences are broken or hard to read.
- 1: most sentences are broken.

Relevance: the choice of content. The summary keeps the most important information of the article, and leaves out details, repetition and side issues.
- 5: the main points of the article, and nothing unimportant.
- 3: some main points are missing, or there is unimportant or repeated content.
- 1: misses the main point of the article.

If a statement is not supported by the article, copy the first such statement into "unsupported" (at most 25 words). Otherwise leave "unsupported" empty.

[user]
<article>
{article}
</article>

<summary>
{summary}
</summary>
