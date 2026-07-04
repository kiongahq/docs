# Engineering blog

Nexus includes a database-backed engineering publication surface:

- `/blogs.html` lists published posts;
- `/blog.html?slug=<slug>` renders one post;
- the landing page shows the newest three posts;
- administrators author drafts and publish from **Engineering blog** in the
  console.

Posts are stored as `blog_post` resources in PostgreSQL in normal deployments
and in the JSON repository in file-backed development. They therefore inherit
tenant isolation, backup behavior, and mutation auditing from the control
plane.

Content is Markdown. The browser renderer escapes stored content before adding
the supported formatting elements, so author-provided HTML and scripts are not
executed. Public APIs return only published posts; draft and write APIs are
administrator-only.

The first persisted article is **Mounting S3 as a filesystem inside Jupyter**,
a general guide based on the workbench's S3FS/FUSE implementation. It covers
object-store semantics, image construction, entrypoint mounts, credentials,
container privileges, readiness, performance, multi-user isolation, production
alternatives, and an operational checklist.
