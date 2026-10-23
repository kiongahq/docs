---
icon: material/text-box-outline
description: Write, review, schedule and publish posts on the Kionga engineering blog, manage editorial members, and configure blog media storage.
---

# Write and publish on the engineering blog

Kionga includes a public engineering blog and a separate **editorial workspace**
for writing, reviewing and publishing posts. Readers use `/blogs.html` (with
search, a tag filter and author pages at `/blogs.html?author=<name>`) and
`/blog.html?slug=<slug>`; the landing page shows the three newest posts. Writers
and editors work at `/editorial.html`.

This guide covers writing a post, reviewing and publishing it, setting up the
editorial team, and configuring media storage.

## Editorial roles {#roles}

Editorial roles are separate from platform roles. A platform administrator cannot
publish without an editorial role.

| Role | Can |
| --- | --- |
| Author | Create posts, edit their own drafts, upload images, submit for review, withdraw |
| Editor | Everything an author can, on any post; request changes, approve and publish, schedule, unpublish, archive, restore |
| Editorial admin | Everything an editor can; add, suspend and remove members, change roles, change blog settings |

## Before you begin

- You sign in with your normal Kionga account, and an editorial admin has added
  you under **Authors** with a role. Personal API keys cannot use the editorial
  workspace.
- To set up the first editorial admin, you need the local bootstrap administrator
  account, or the platform `admin` role with single sign-on.
- To configure media storage, you need access to the gateway's environment.

## Write a post

1. Open `/editorial.html`, or in the console open **Engineering blog** and click
   **Open editorial workspace**.
2. Click **New post**. Type a title (the slug follows it until you edit the slug),
   a one-line summary, and the body.
    - Press **Tab** or **+** to add headings, lists (bulleted, numbered,
      checklist), quotes, code, tables, notes, dividers and images.
    - Select text for bold, italic, links, inline code and highlight.
    - Paste a YouTube, Vimeo or GitHub gist URL to embed it.
3. Add images: choose a file, drag it onto the editor, or paste it. Fill in the
   **Alt text** (required to publish), an optional caption and the alignment.
4. Set tags, a cover image with alt text, and an optional SEO title and
   description. The social card preview updates as you type.
5. Click **Preview** to see the post as readers will, at desktop width or phone
   width.
6. Click **Submit for review**. The post becomes read-only for you until an editor
   publishes it or requests changes. Click **Withdraw** to take it back.

Changes save automatically, and Ctrl+S (⌘+S on macOS) saves at once. The status
next to the post badge shows whether the post is saving, saved, or kept locally
while offline. If the browser or network fails, reopening the post offers to
restore your changes. If someone else saved in the meantime, you choose to keep
yours or load theirs.

**History** lists every save. Select two revisions to compare them, or restore an
older one as a new revision. **Focus** hides everything except the canvas (press
<kbd>Esc</kbd> to leave it). **Import Markdown** appends converted blocks, and **Export
Markdown** downloads the post.

**Verify:** the post appears under **Reviews** for editors, with the status
waiting for review.

## Review and publish a post

You need the editor or editorial admin role.

1. Open **Reviews** and open a post.
2. Read it in **Preview**.
3. Choose one action:
    - **Approve & publish** to publish now.
    - **Schedule** to publish later: pick the date and time first. The post goes
      live within about 20 seconds of that time.
    - **Request changes** to return it to the author as a draft.

Publishing is blocked until every image and the cover have alt text. Editors can
fix typos on published posts; those saves go live at once and are kept as
revisions.

To take a post down, click **Unpublish** (back to draft) or **Archive** (hidden).
**Restore from archive** brings an archived post back as a draft.

**Verify:** the post appears on `/blogs.html`.

## Set up the editorial team

1. The first time, sign in as the local bootstrap administrator (or as a platform
   `admin` with single sign-on), open `/editorial.html`, and click **Become the
   first editorial admin**. This works only while no active editorial admin
   exists, and it is audited.
2. Open **Authors** and click **Add member**. Enter the person's platform
   identity (the local username, or the single sign-on subject) and choose a role.
3. To change a member later, change their role, suspend them, or remove them under
   **Authors**.

The last editorial admin cannot be removed, demoted or suspended. An editorial
session lasts 4 hours, and membership is checked on every request, so removing a
member takes effect at once.

**Verify:** the new member can open `/editorial.html` and sees the actions of
their role.

## Configure media storage

Blog images go to the `kionga-blog-media` bucket, which the Compose stack creates
and configures for you. To use other storage, set these variables on the gateway
and restart it:

| Variable | Default | Meaning |
| --- | --- | --- |
| `KIONGA_BLOG_MEDIA_BACKEND` | `s3` when an endpoint is set, otherwise `fs` | `s3` or `fs` |
| `KIONGA_BLOG_MEDIA_S3_ENDPOINT` | none | For example `http://objectstore:9000` |
| `KIONGA_BLOG_MEDIA_S3_ACCESS_KEY`, `KIONGA_BLOG_MEDIA_S3_SECRET_KEY`, `KIONGA_BLOG_MEDIA_S3_REGION` | none, none, `us-east-1` | Credentials and region |
| `KIONGA_BLOG_MEDIA_BUCKET` | `kionga-blog-media` | Bucket |
| `KIONGA_BLOG_MEDIA_DIR` | `data/blog-media` | Root folder for the `fs` backend |

Upload limits: 10 MB per file; JPEG, PNG, WebP or GIF (checked from the file
contents); at most 12,000 pixels per side and 50 megapixels. Kionga applies the
image orientation, removes EXIF and other metadata, keeps only the first frame of
an animated GIF, and deletes unattached uploads after 24 hours. Back up the media
bucket together with PostgreSQL.

The scheduled publisher honors `KIONGA_SCHEDULER=off` like the pipeline
scheduler, and only one gateway replica publishes at a time. The gateway metrics
include `kionga_editorial_saves_total`, `kionga_editorial_transitions_total`,
`kionga_editorial_media_uploads_total` and
`kionga_editorial_scheduled_publishes_total`.

**Verify:** an image uploaded in a post displays in **Preview** and on the
published page.

## Related

- For the design of the editor and editorial identity, see the
  [engineering handbook](https://kiongahq.github.io/docs/engineering/decisions/0002-blog-editor/).
