---
description: The MADR 4 template for Kionga architecture decision records, with the house conventions for status, dates and evidence.
status: "proposed"
date: YYYY-MM-DD
---

# Short title of the problem and the chosen solution

Copy this file to `NNNN-short-title.md` with the next free number, fill it in, add
it to [the decision log](index.md), the navigation in `engineering/mkdocs.yml` and
[architecture section 9](../architecture/09-architecture-decisions.md), and open a pull
request. The structure is [MADR 4](https://adr.github.io/madr/); headings are in
sentence case to match the rest of the handbook. Delete optional sections you do not
use, and delete this paragraph.

Front matter fields:

- `description`: one sentence that names the decision.
- `status`: `proposed`, `accepted`, `rejected`, `deprecated`, or
  `superseded by NNNN`.
- `date`: when the decision was last updated, as `YYYY-MM-DD`.
- `decision-makers`, `consulted`, `informed` (optional): the people involved.

## Context and problem statement

Describe the context and the problem in two or three sentences, or as a short story.
State the problem as a question if that helps. Link to issues or discussions.

## Decision drivers

Optional. The forces and concerns that the decision must satisfy:

- Driver 1, for example a quality goal or a constraint.
- Driver 2.

## Considered options

- Option 1
- Option 2
- Option 3

## Decision outcome

Chosen option: **Option 1**, because it is the only option that meets driver 1, or
because it comes out best in the comparison below.

### Consequences

Optional.

- Good, because of a positive consequence, for example an improved quality.
- Bad, because of a negative consequence, for example a compromised quality.

### Confirmation

Optional. How compliance with the decision is checked: a test, a CI step, a review
rule. Name the file or job.

## Pros and cons of the options

Optional.

### Option 1

An example, a description, or a link to more information.

- Good, because of argument a.
- Neutral, because of argument b.
- Bad, because of argument c.

### Option 2

- Good, because of argument a.
- Bad, because of argument b.

## More information

Optional. Evidence for the outcome, how and when the decision is carried out, when to
revisit it, and links to related decisions. For a record written after the fact, list
the commits and files that establish the decision.
