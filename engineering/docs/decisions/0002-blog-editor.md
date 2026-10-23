---
description: Use Editor.js block content rendered and sanitized on the server for the engineering blog, with editorial roles and a session separate from platform roles.
status: "accepted"
date: 2026-10-09
---

# 0002 Blog editor, canonical content and editorial identity

## Context and problem statement

Kionga publishes an engineering blog, written in a separate editorial workspace
(`/editorial.html`) and read on public pages without signing in. Three questions had
to be answered together:

1. Which editor do authors use, given that the console and public site are plain
   scripts with no build step?
2. What is the canonical stored form of a post, and how is it made safe to publish?
3. Who may write and publish, given that publishing to a public site is a different
   trust domain from operating ML infrastructure?

## Decision drivers

- No bundler: every browser dependency must load as a plain script embedded with
  `go:embed`.
- Structured content that can be diffed per block and rendered on the server, without
  parsing HTML from the browser.
- Deterministic revision comparison.
- Alt text on every image, and images only from Kionga's own media endpoint.
- Publishing rights independent of ML administration rights, with per-person roles
  that editorial administrators manage themselves.
- Local mode has no identity-provider groups.

## Considered options

Editor:

- Editor.js
- `Tiptap`
- Lexical
- A Markdown text area (the previous editor)
- Quill

Editorial identity:

- A separate editorial membership with its own session, on top of the platform identity
- An OIDC group claim such as `kionga-editors`
- An editorial role inside `UserAccess`
- Reusing the ML platform roles

## Decision outcome

Chosen options:

1. **Editor.js**, because it ships browser-ready UMD builds, saves structured block
   JSON, and gives every block a stable ID. Editor.js 2.31.7 and the official header,
   list, quote, code, delimiter, embed, table, inline-code, marker and warning tools are
   vendored as upstream UMD builds under
   `platform/go/cmd/gateway/web/vendor/editorjs/` with their licenses.
2. **Block JSON as canonical content, rendered and sanitized on the server**, because
   it is structured, comparable per block, and rendered without trusting browser HTML.
3. **A separate editorial membership and session**, because it is the only option that
   keeps publishing out of ML administration and works in local mode.

### Consequences

- Good, because each block registers one global from a browser-ready file, so nothing
  needs a build step.
- Good, because blocks are matched by ID, not position, so revision comparison is
  deterministic.
- Good, because a stolen console cookie does not reach the public site: editorial
  access needs its own session.
- Good, because ML administrators have no publishing rights unless they are members,
  and writers need no platform administration reach.
- Bad, because `@editorjs/image` could not be used (see below), so Kionga maintains a
  small image tool.
- Bad, because Editor.js has no undo or redo module; Kionga keeps a block-level
  snapshot history in `editorial/state.js`, and text-level undo is the browser's own.
- Neutral, because Markdown remains only as an optional import and export.

### Confirmation

- `platform/tests/ui/vendor-integrity.test.cjs` recomputes the vendored hashes on every
  gate run and fails if a page references a vendored file without its pinned hash.
- `platform/go/internal/editorial/workflow_test.go` and the editorial tests in
  `platform/go/internal/httpapi/blog_test.go` cover roles, transitions and publishing
  rules; `platform/tests/e2e/editorial.spec.cjs` covers author, editor, the public page
  and a denied ML user in a browser.

## Pros and cons of the options

### Editor.js

- Good, because it ships browser-ready UMD files and saves
  `{blocks: [{id, type, data}]}`.
- Good, because block IDs are stable.
- Bad, because there is no undo or redo module.

### `Tiptap`

- Bad, because it is distributed as ES modules over ProseMirror, so a production setup
  needs a bundler or a large import map of ProseMirror packages.
- Bad, because its output is ProseMirror JSON or HTML, which pushes HTML sanitizing of
  the whole document to the server anyway.

### Lexical

- Bad, because it has the same bundler requirement (React-first packaging, ESM only);
  vanilla use is possible but not documented for a no-build setup.

### Markdown text area

- Bad, because authors had to know Markdown, there was no media workflow and no
  structured diff.

### Quill

- Bad, because its Delta format is not block-structured, and image and embed handling
  would still need custom tools.

### `@editorjs/image`

Evaluated and not used.

- Bad, because it has no alt-text field, no alignment, no upload progress, and stores
  a free URL. Publishing requires alt text and images must come only from Kionga's
  media endpoint, so the workspace ships a small local block tool
  (`editorial/image-tool.js`) that stores a `media_id`.

### Separate editorial membership and session

- Good, because publishing is a separate trust domain from operating ML
  infrastructure.
- Good, because editorial administrators manage per-person roles themselves.

### OIDC group claim

- Bad, because local mode has no groups, and memberships need per-person roles that
  editorial administrators manage themselves. Rejected for now.

### Editorial role inside `UserAccess`

- Bad, because it would put publishing back under ML administrators.

### Reusing ML roles

- Bad, because every platform operator would become a publisher and every writer a
  platform user with administration reach.

## More information

### Supply chain

`platform/scripts/vendor-manifest.py` compares every vendored file with the SHA-256
that the `jsDelivr` package API publishes for the same pinned npm version (a channel
independent of the download) and writes `MANIFEST.json` with the SHA-384 used for
integrity. `editorial.html` loads each script with `integrity`;
`blog.html` pins highlight.js 11.11.1 ES modules through an import map `integrity`
table. The npm `latest` dist-tag of `@editorjs/editorjs` points at a `0.0.0` preview of
a rewrite; 2.31.7 (the `next` tag) is the latest 2.x release and is the pinned version.

### Canonical content

- Stored: block JSON (`editorial_post.blocks`). Markdown is never required.
- On save, `editorial.NormalizeBlocks` validates every block type, clamps enumerated
  values and rebuilds inline HTML from an allowlist (`b`, `i`, `a[href]`, `code`,
  `mark`, `br`, `s`, `u`). Links get `rel="noopener noreferrer nofollow"`; only HTTP,
  HTTPS, `mailto:`, site-relative and `#` links survive.
- On read, `editorial.Render` turns blocks into HTML and passes the result through a
  `bluemonday` policy narrowed to exactly what the renderer emits: images only from
  `/media/blog/<id>/<480|960|1600>`, iframes only from
  `youtube-nocookie.com/embed/<id>` and `player.vimeo.com/video/<id>` with a
  `sandbox`, GitHub `gist` embeds as plain links, no `style`, no `data:` URLs. The embed
  URL a client sends is ignored; it is rebuilt from the validated source URL.
- The public page inserts only `rendered_html` as markup; every other field is escaped
  in the browser.
- Posts stored as Markdown (including the seed post) are converted to blocks once at
  startup (`MigrateLegacy`), keeping ID, slug, author, status and dates, and keeping
  the original in `legacy_markdown`.

### Editorial identity

Editorial access is a membership (document kind `editorial_member`, roles `author`,
`editor`, `editorial_admin`) on top of the same verified platform identity (local
account or OIDC), with its own cookie.

- `POST /api/v1/editorial/session` mints `kionga_editorial` (`Path=/`, `HttpOnly`,
  `SameSite=Strict`, `Secure` behind TLS or OIDC, four-hour lifetime) only for an
  active member. The server stores only the SHA-256 of the token.
- Every `/api/v1/editorial/*` request needs that session (`403` otherwise), the
  membership is read again on every request (removal or suspension is immediate), and
  the session subject must equal the signed-in platform subject, so a leftover cookie
  cannot be used by another person on a shared browser. Mutations with
  `Sec-Fetch-Site: cross-site` are refused on top of `SameSite`.
- The gateway RBAC lets every human principal reach `/api/v1/editorial/*` and lets the
  membership decide; service identities and API keys never reach it.
- Bootstrap: while no active `editorial_admin` exists, the local bootstrap
  administrator (local mode) or an ML administrator may grant themselves the first
  `editorial_admin` through `POST /api/v1/editorial/bootstrap`. The call is audited and
  serialized by a create-only claim document. The last active editorial administrator
  cannot be demoted, suspended or removed, so bootstrap does not reopen.

### Workflow, revisions, scheduling, media

- States: `draft`, `in_review`, `scheduled` or `published`; unpublish returns to
  `draft`; `archive` and `restore`. Authors create, edit their own drafts and submit or
  withdraw; editors also review, request changes, publish, schedule, unpublish and
  archive; editorial administrators also manage members and settings. Publishing
  requires a title, a summary, at least 20 words, and alt text on every image and the
  cover.
- Every content save writes an immutable `blog_revision`; unchanged autosaves do
  nothing. `PUT` takes `base_revision`; a stale base returns `409` with the latest
  post. Restore creates a new revision and keeps the post's slug.
- Scheduled publishing reuses the scheduler pattern: a lease document picks one
  replica, and the per-post row lock plus a status check make double publication
  impossible even if two replicas both act as leader.
- Media: multipart upload up to 10 MB, type detected from the bytes (JPEG, PNG, WebP,
  GIF; file name and client type ignored), dimensions bounded before decoding, EXIF
  orientation applied, then re-encoded (which drops all metadata) into 480, 960 and
  1600 pixel variants. Bytes go to a `MediaStore`: any S3 store (RustFS locally) with
  SigV4 presigned requests, or the file system for local development and tests.
  Uploads are `pending` until a save references them (`attached`); pending items older
  than 24 hours are removed. `/media/blog/{id}/{variant}` is public only while the media
  is attached to a published post that still references it.

The record was written with the editorial workspace and block-based blog in the
`platform` repository (commit `10eb048`, 2026-10-09). The user guide is
[engineering blog](https://kiongahq.github.io/docs/guides/engineering-blog/).
