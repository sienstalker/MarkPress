---
title: Writing a new page
date: 2026-09-23
---

Create a file in the `content/` folder, for example `my-notes.md`. The file name becomes the page address, so `my-notes.md` is published as `my-notes.html`.

Start the file with a front-matter block:

```
---
title: My notes
date: 2026-09-26
draft: false
---
```

All three fields are optional. Without a title, MarkPress uses the file name. Pages marked `draft: true` are skipped when the site is built.

> Dates must use the YYYY-MM-DD format. A wrong date fails the build instead of publishing a broken page.
