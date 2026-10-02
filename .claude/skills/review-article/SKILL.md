---
name: review-article
description: Proofread a blog article in docs/articles/posts. Checks facts, code,
  grammar, typos and consistency, then reports findings without editing. Use when
  the user asks to review, proofread or fact-check an article.
argument-hint: "[path to article; defaults to the most recently modified post]"
---

# Review an article

## Find the article

Use `$ARGUMENTS` if a path is given. Otherwise pick the post in
`docs/articles/posts/` with the most recently modified `index.md`
(`ls -t docs/articles/posts/*/index.md | head -1`).

Read the whole file, and look at any images it references.

## What to check

1. **Facts.** Technical claims, terminology, numbers, and outputs. Where code
   output is shown, verify it is what the code would actually print (bit
   patterns, formatting, rounding). Flag claims that hold only on some
   platforms, compilers, or language standards.
2. **Code.** Does every snippet compile and do what the prose says? Watch for
   variables that are declared but not used, snippets that disagree with each
   other, and output blocks that don't match the code above them.
3. **Grammar and typos.** Spelling, punctuation, comma splices, its/it's,
   a/an, past tenses ("casted" → "cast"), doubled spaces, repeated words.
4. **Consistency.** British vs American spelling, terminology used for the
   same concept, code formatting of identifiers in prose, hard-wrapped vs
   unwrapped paragraphs, trailing whitespace.
5. **Front matter.** Valid date (posts go live at 12:00 UTC), slug,
   categories, tags. Flag if the date doesn't match the folder name.
6. **Clarity.** Only flag sentences that are genuinely confusing. Don't
   rewrite the author's voice or casual tone.

## Output

Do not edit the article unless asked. Report findings grouped as:

- **Errors** (factual or code mistakes; things a reader would call out)
- **Grammar and typos**
- **Style and consistency** (optional suggestions)

Reference each finding as `path:line` with a short suggested fix. Keep it
terse. End by offering to apply the fixes.
