# Bilingual Vocabulary Highlight Standard

Status: production standard
Scope: every exam year and article in `kaoyan-reader-v1`, from 2002 through all future years.

## Goal

Vocabulary emphasis is bilingual. If an English vocabulary occurrence is designated level 6 or above, the reader should also emphasize the faithful corresponding phrase in the existing Chinese translation whenever that correspondence can be represented as one or more exact reviewed Chinese spans.

The English highlight and Chinese highlight are one editorial relationship, not two independent decorations.

## Canonical contract

Each required occurrence is identified by:

- article id;
- sentence id;
- exact English character start/end offsets;
- exact English source text.

A reviewed mapping contains one or more Chinese spans, each with:

- exact Chinese character start/end offsets;
- exact Chinese source text.

Mappings are occurrence-specific. Repeated words in the same sentence must not rely on an ambiguous first-match rule.

## Study gloss is separate from translation alignment

Every selected word or multi-word phrase must carry a non-empty Chinese `study_gloss` for the vocabulary/phrase book. This learning gloss is a separate data product from the Chinese translation highlight.

- `study_gloss` may be curated or generated from the phrase and its sentence context during content production.
- The vocabulary/phrase book displays `study_gloss` even when the existing sentence translation has no clean corresponding span.
- A study gloss must never be injected into the sentence translation, and must never be used to fabricate `zh_spans`.
- If no faithful exact reviewed Chinese span can be represented, the occurrence is stored as an exception with `kind: "study_gloss_only"`, a non-empty `study_gloss`, and no Chinese highlight span.
- Runtime rendering may consume the stored study gloss, but it must not perform fuzzy Chinese matching to create a correspondence after publication.

## Required coverage

1. Every vocabulary occurrence with `level >= 6` is required coverage.
2. Each required occurrence must be covered by exactly one valid mapping, or by one explicit alignment exception with a non-empty reason. A `study_gloss_only` exception must also carry a non-empty `study_gloss`.
3. Publication QA must satisfy:
   `required_occurrences == mapped_occurrences + reviewed_exceptions`.
4. Stale English offsets, stale Chinese offsets, nonexistent sentences, duplicate mappings, and unreviewed missing occurrences are publication failures.
5. Reviewed exceptions are for genuine translation restructuring where no faithful contiguous Chinese span exists; they are not a shortcut for incomplete editorial work.

## Editorial rules

- Preserve the existing English and Chinese wording byte-for-byte.
- Do not rewrite a translation merely to make highlighting easier.
- Highlight the phrase that actually carries the concept in the Chinese translation, not mechanically the shortest dictionary gloss.
- A single Chinese phrase may legitimately correspond to more than one English vocabulary item where the translation combines concepts.
- If the translation expresses an English term through a larger natural phrase, highlight that faithful phrase.
- Runtime fuzzy matching, runtime AI translation, dictionary lookup, and semantic guessing are prohibited for Chinese sentence alignment. Production-time study-gloss generation is allowed, but its output belongs only to the vocabulary/phrase-book field unless an exact reviewed translation span is independently established.

## Storage and rendering

Reviewed canonical mapping sources live under:

`content-pipeline/curated/bilingual-highlights/<year>.json`

Reader-ready mappings live under:

`kaoyan-reader-v1/content/<year>/bilingual-highlights.json`

The reader loads the mapping by the selected exam year. Rendering remains year-neutral: `renderChinese()` validates the exact source ranges and wraps valid mapped spans with the shared `vocab zh-vocab` styling.

## QA and publication gate

The strict validator must report, per year:

- `required_occurrences`;
- `mapped_occurrences`;
- `reviewed_exceptions`;
- `errors`.

A year is publishable only when `errors` is empty and full required coverage is accounted for. The publish workflow must rerun this validation before updating the Pages branch.

For the reviewed 2003-2006 rollout, the locked required inventory is:

- 2003: 71 occurrences;
- 2004: 85 occurrences;
- 2005: 24 occurrences;
- 2006: 28 occurrences;
- total: 208 occurrences.

Any future change to that inventory requires editorial review rather than silently changing the expected counts.

## Compatibility

2002's already-reviewed bilingual mappings must remain visually intact. The loader may temporarily accept its legacy article keys while the runtime API remains year-neutral. Future years must use the same contract rather than adding year-specific rendering logic.

## Verification

A bilingual-highlight change is acceptable only when:

- validator unit tests cover valid mappings, stale spans, nonexistent/missing occurrences, duplicates, and reviewed exceptions;
- build tests prove invalid mappings refuse publication;
- all published year mappings rebuild with zero validator errors;
- the reader unit suite passes;
- browser smoke checks confirm both English and Chinese highlighting on 2002 and on at least one V4 year;
- no translation text, vocabulary level, actor assignment, or audio asset was altered solely for highlighting.

This standard is mandatory for later 2007-2026 production.
