# 3. The questionnaire agent drafts only from approved, unexpired evidence

**Status:** accepted

Security reviews are where law-firm rollouts stall, and a wrong answer in one is a contractual statement. The agent
retrieves with BM25 over an approved evidence library and drafts only when the best match clears a score, beats the
runner-up by a margin, and covers the question's informative words. Otherwise the question goes to the security team.
Every draft cites its evidence id and is approved by a person. An optional Claude rephraser may reword the evidence to
fit the question; code throws the rewording away if it drops the citation or contains a number the evidence does not.

We chose retrieval with hard rules over a model deciding, because the cost of a confident wrong answer is far higher
than the cost of a question going to a person.
