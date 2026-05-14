# assets/

Visual assets for the project's docs and public surface.

| File | Status | Used by |
|---|---|---|
| `hero.png` | **In use** — figure-in-stance illustration, skill exchange with the registry | `README.md` hero |
| `logo.svg` | **Placeholder mark** — typographic, pending a designed vector mark | favicon / avatar / social (not yet wired) |
| `demo.svg` | **Not yet produced** — terminal cast of the install flow | `README.md` Quickstart |

---

## Hero — done

`hero.png` is the README hero: an agent figure in a martial-arts stance exchanging skill data with the registry (data flowing in *and* back out — acquire and contribute). Generated, then resized to 1280px wide and compressed. It is a raster illustration — fine as a hero, but it is **not** a scalable mark (see below).

## Vector mark — what to produce

`logo.svg` today is a plain typographic placeholder. A proper vector **mark** is still needed for the small surfaces a raster hero cannot serve:

- **Work at small sizes** — favicon (16–32px), GitHub org avatar, Discord server icon. Must stay legible when tiny.
- **Be a simple, geometric vector** — flat, 2–3 colors. Could derive from the strongest single element of the hero (e.g. the head + data-in/out, abstracted), not the whole figure.
- **Ship as SVG** (primary, version-controlled as text) plus a **PNG export** at 2x.
- **Stay original.** Lean into the "instantly acquire a skill" metaphor through *language* in the copy, not through imagery that evokes a specific film. (Decision context: session-9 discussion.)

Suggested file set when the mark lands: `logo.svg` (mark), `logo.png`, `logo-dark.svg` (if a dark-mode variant is wanted).

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
