# assets/

Visual assets for the project's docs and public surface.

| File | Status | Used by |
|---|---|---|
| `logo.svg` | **Placeholder** — clean wordmark, replace with a designed logo | `README.md` hero |
| `demo.svg` | **Not yet produced** — terminal cast of the install flow | `README.md` Quickstart |

---

## Logo — what to produce

`logo.svg` today is a plain typographic placeholder so the README hero is not a broken image. The real logo should:

- **Stay abstract and original.** Lean into the "instantly acquire a skill" metaphor through *language* in the copy, not through imagery that evokes a specific film — that edges into third-party trademarked visuals and buys no real recognition. (Decision context: session-9 discussion.)
- **Work as a horizontal lockup** (mark + wordmark) at roughly 520×120, and as a standalone square mark for favicons / social cards.
- **Ship as SVG** (primary, version-controlled as text) plus a **PNG export** at 2x for surfaces that do not render SVG.
- **Read on a light background** — the README renders on white/light GitHub chrome.

Suggested file set when the designed logo lands: `logo.svg`, `logo.png`, `logo-mark.svg` (square mark only), `logo-dark.svg` (if a dark-mode variant is wanted).

## Terminal cast — what to produce

`demo.svg` should be a short, silent cast of the consumer happy path so a reader sees the tool work without installing it. Record these commands, in order, against a populated registry:

```
kfu update
kfu search <a real query that returns hits>
kfu install <author>/<skill>
kfu list
```

Recommended tooling — produces a **version-controllable SVG** rather than a heavy GIF:

```
# record
asciinema rec demo.cast
# convert to SVG
npx svg-term-cli --in demo.cast --out assets/demo.svg --window --width 80 --height 24
```

A GIF is acceptable as a fallback (`assets/demo.gif`) if SVG conversion is awkward, but SVG keeps the repo light and diffable. Keep the cast under ~20 seconds; trim dead time.

Once `demo.svg` exists, drop it into the README Quickstart section — there is a placeholder comment there marking the spot.
