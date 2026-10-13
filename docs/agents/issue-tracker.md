# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Task state is recorded as a `Status:` line near the top of each issue file. Until a triage workflow is configured, use `open`, `claimed`, or `resolved`.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## Working materials

- Keep feature-specific requirements in `.scratch/<feature-slug>/spec.md`.
- Keep research, references, and unresolved questions in `.scratch/<feature-slug>/notes.md`; put supporting files in `.scratch/<feature-slug>/assets/` when needed.
- Keep implementation tickets in `.scratch/<feature-slug>/issues/` using the numbered filenames above.
- Keep shared, maintained project documentation in `docs/`. Existing files include `product-design.md`, `api.md`, `schema.sql`, and `verification.md`; screenshots live in `docs/screenshots/`.
- Put settled domain terminology in root `GLOSSARY.md` and architecture decisions in `docs/adr/`, following `docs/agents/domain.md`. Create them only as terms or decisions are resolved.
- Use short, stable feature slugs such as `question-bank` or `practice-session`; create files only when there is real content to record.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
