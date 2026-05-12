# Naming decision — full session record (2026-05-12)

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Outcome | Project renamed `agent-skills` → **I Know Kung Fu** |
| ADR | `docs/decisions.md` § ADR-001 |
| GitHub action taken | `gh repo rename iknowkungfu` — `samuelgudi/agent-skills` is now `samuelgudi/iknowkungfu` (still PRIVATE) |
| Code action taken | None — codebase rename is deferred to session-6 Phase 1 |
| Probes executed | ~100 across PyPI, GitHub, domains (.com/.io/.ai/.dev), brand search, trademark search |
| Candidates evaluated | ~40 across 6 naming registers |

This file documents the full naming process, the frameworks applied, the alternatives evaluated, and why the surface-level "obvious" choices kept failing. **Read this before re-litigating the name** — most of the obvious alternatives have already been probed and the data is here.

---

## 1. The problem we were solving

The project needs a name that:

1. Is **available on PyPI** — `pip install <name>` must work.
2. Has clean `.io` / `.ai` domain availability (`.com` desirable but optional).
3. Doesn't collide with existing **AI/agent-space brands** in trademark or SEO.
4. Differentiates from **15+ direct or near-direct competitors** in the agent-skills-registry space.
5. Captures the project's **actual positioning** — a structured commons where AI agents are *citizens* (consume, supply, AND maintain skills), not a marketplace where humans publish and agents consume.

Pre-existing constraint: PyPI namespace `agent-skills` is taken by `datalayer/agent-skills` (unrelated Jupyter tool). Cannot publish under the working name.

---

## 2. The four expert frameworks applied

To avoid undisciplined "throw spaghetti, react on vibes" brainstorming, the session pulled four authoritative naming frameworks and applied them as filters.

### 2.1 Alexandra Watkins — SMILE & SCRATCH test

Watkins runs Eat My Words (Amazon, Coca-Cola, Disney, Google as clients). Her 12-point filter:

**SMILE** (5 qualities to chase):
- **S**uggestive — evokes brand essence
- **M**emorable — distinctive, sticky
- **I**magery — paints a visual
- **L**egs — extends to story / merch / themes
- **E**motional — moves people

**SCRATCH** (7 deal-breakers):
- **S**pelling-challenged (looks like a typo)
- **C**opycat (resembles competitors)
- **R**estrictive (boxes you in)
- **A**nnoying (forced, cutesy)
- **T**ame (flat, descriptive, uninspired)
- **C**urse of knowledge (insider-only)
- **H**ard to pronounce

### 2.2 Igor — 4 types of brand names

- **Functional**: literal description (*RideCharge, Infoseek*) — weakest category in modern naming.
- **Experiential**: direct human experience + imagination (*Lyft, Vercel, Palm Pilot*).
- **Evocative**: evokes positioning (*Apple, Virgin, Azure, Sonos*).
- **Invented**: coined, no prior meaning (*Google, Verizon, Kodak, Pentium*).

Lexicon's billion-dollar portfolio skews heavily toward Evocative and Invented. Functional names rarely become great brands.

### 2.3 David Placek / Lexicon Branding

Lexicon named Sonos, Azure, Vercel, Windsurf, Impossible Foods, BlackBerry, Pentium, Swiffer. Key principles:

- **"Surprising, but surprisingly familiar"** — the sweet spot.
- **Diamond framework** — before brainstorming words, define behavior: Win (top), What we have to win (right), What we need to win (bottom), What we need to say (left).
- **Sound symbolism** — phonemes carry meaning independently of semantics. Hard consonants (P, K, T) feel sharp/tech; soft (S, M, L) feel friendly; open vowels (A, O) feel inclusive.
- **Volume discipline**: Lexicon generates 1,000-1,500 names per engagement before finding the gem. We evaluated ~40.

### 2.4 Competitive-landscape audit

Before naming, map every competitor to avoid Copycat:

- Skyll · agensi.io · skillcreator.ai · skills.sh · skild.ai · openskills (numman-ali) · addyosmani/agent-skills · markdav-is/Skiller · VoltAgent/awesome-agent-skills · mattpocock/skills · agent-skills-hub · agentskillshub.dev · iflytek/skillhub · qufei1993/skills-hub · ClawHub · tech-leads-club/agent-skills · openclaw/skills · haabe/mycelium · Skales (skalesapp) · Kiln-AI/Kiln · Solo.io agentregistry · Roost.ai · Asteria Corp/AI · Aurelia framework

**~22 direct or near-direct competitors logged** during this session — far more than the session-5 handoff's "Skyll is the competitor" estimate suggested.

---

## 3. The Diamond for this project

```
                            WIN
              (default trust layer where AI
               agents collectively publish,
               consume, and maintain their craft)
                             |
What we need to say  ─────── ◇ ───────  What we have to win
(the structured                          (agent-as-citizen model,
 commons where agent-                    immutable versioning,
 citizens transmit                       content hashes, yank/
 their craft, and the                    deprecate, GitHub-ID
 corpus rises with                       author binding, sanitize
 every contribution)                     + security_scan pipeline,
                                          multi-host adapters — none
                                          of the 15+ competitors
                             |            have this combination)
                       What we need
                          to win
            (trust of agent stewards +
             ecosystem embrace by
             agentskills.io + fast grok)
```

The brand essence: **"the structured commons where AI agents collectively transmit and maintain their craft, and it grows with every passing contributor."**

---

## 4. The candidate evaluation — namespace exhaustion in 2026

Probed candidates by register, with availability after PyPI + domain + brand check.

### Register A — Functional compounds (`skill-X`, `agent-X-hub`)

| Candidate | Verdict |
|---|---|
| skill-library | Tame, Restrictive |
| skill-engine | Contested by skillengine.world, skillsengine.com, skillengine.co.uk |
| skillable | Brand: skillable.com (20-year virtual-labs incumbent, Microsoft/IBM/Intel partner) |
| skilled | Tame, generic adjective |
| skiller | PyPI taken; direct competitor `markdav-is/Skiller` does skills-as-memory for AI agents |
| skill-engine | Multiple HR brands |
| oh-my-skills | Direct competitor `akillness/oh-my-skills` already exists in Claude marketplace |
| skillex | Live product skillex.ai (skills mgmt, 500+ teams) |
| skillmesh | PyPI taken; skillmesh.com parked for sale |
| AgentSkillHub | **5+ direct competitors with same letter pattern** (agent-skills-hub, agentskillshub.dev, iflytek/skillhub, qufei1993/skills-hub, tech-leads-club/agent-skills) |
| everskill | Brand: Everskill GmbH (Munich EdTech, $5M revenue) |

**Result: 0 of 11 viable.** Watkins flagged "T-Tame" and "C-Copycat" universally.

### Register B — Evocative English words

| Candidate | Verdict |
|---|---|
| cairn | PyPI taken; AI background-agent competitor `cairn-dev/cairn` |
| tessera | PyPI taken |
| vela | PyPI taken |
| mycelium | PyPI taken (abandoned); 3+ live brands; AI competitor `haabe/mycelium` Claude plugin |
| praxis | PyPI taken; direct competitor `prxs.ai` ("distributed registry for AI agent discovery") |
| solera | Brand: Solera Inc. (massive automotive AI software co, formerly NYSE-listed) |
| skira | Skira Editore (Italian art publisher, 1928) + Skira AB + Skira AI video tool |
| crucible / atrium / almanac / hearth / tarn / quoin | All PyPI-taken |
| aurelia / arete / asteria / elora | All PyPI-taken + heavy AI brand contestation |

**Result: 0 of 14 clean.**

### Register C — Playful short nouns (OpenClaw register)

| Candidate | Verdict |
|---|---|
| kiln | PyPI taken; **direct competitor `Kiln-AI/Kiln`** ("Build, Evaluate, Optimize AI Systems. Skills feature.") |
| hatch | PyPI taken — **THE official PyPA Python project manager** |
| mint | PyPI taken; Mintlify ($45M Series B, $500M valuation) |
| roost | Brand: Roost.ai (AI testing copilot) |
| spool | PyPI taken |
| magpie / heron / crane / owl / glean / croft / cask / lathe | **All 8 PyPI-taken (100% squatting rate)** |

**Result: 0 of 13 clean.** This is the conclusive evidence of namespace exhaustion: **every short concrete English noun tested was PyPI-squatted as of May 2026.**

### Register D — Coined / invented names

Probed with deliberate sound-symbolism for our brief (soft+rising for Italian-lyrical OR hard+decisive for infrastructure):

| Candidate | PyPI | Brand | Verdict |
|---|---|---|---|
| Velora | Taken | 5+ AI brands | Dead |
| Solvi | Free | Multiple AI brands | Contested |
| Plenix | Free | Minor non-AI brands | Mild collision |
| Akra | Free | akra.ai healthcare AI | Contested |
| Telva | Free | Spanish fashion mag + Finnish defence | Cross-industry |
| Corvex | Free | **corvex.ai AI cloud computing** | Direct AI competitor |
| **Evria** | **Free** | No AI competitor | **Clean** |
| Kairn | Free | Kairntech enterprise agentic AI | Direct competitor |
| Meridion | Free | Mild adjacency only (Meridian AI) | Clean-ish |
| Avenia | Free | No collision | **Clean** |
| **Aurika** | **Free** | No collision | **Clean** |
| **Korva** | **Free** | No collision (Finnish "ear" — harmless) | **Clean** |

**Result: 5 of 12 clean.** This is the only register with reliable available namespace.

### Register E — Controlled-misspellings / homophones

| Candidate | Verdict |
|---|---|
| Nolege (= Knowledge) | PyPI free, but **Nolej AI** (€3M Series A, edtech) is too phonetically close — trademark confusion risk |
| Knolege | PyPI free, same Nolej adjacency, plus Watkins "S-Spelling-challenged" |
| Skeel (= Skill) | **Not a homophone in English** (long-E vs short-I); phonetic neighbors Skell.ai, Skales, Skeells, Skild — 4 AI brands within 1 letter |
| EvrySkyll | Same `skill*` saturation, plus spelling-challenged |
| Oreka (= Eureka) | PyPI taken (OrecX call-recording); `oreka.io` taken by coworking SaaS; **`Orkes` just raised $60M for AI agent orchestration** (phonetic neighbor) |

**Result: 0 of 5 clean.**

### Register F — Cultural-reference / OpenClaw register

| Candidate | Verdict |
|---|---|
| Construct (Matrix loading program) | PyPI taken — heavily (70+ releases of `construct` binary-parsing library) |
| kungfu | PyPI taken (v1.0.0 → 1.7.1) |
| **iknowkungfu** | **PyPI free, no trademark, no phrase collision** |

`I Know Kung Fu` survived clean.

---

## 5. Why "I Know Kung Fu" won the final round

Even with Aurika, Korva, Evria as cleared coined-name backups, the cultural-reference name beat them on every Watkins SMILE dimension:

| Dimension | Aurika / Korva / Evria | I Know Kung Fu |
|---|---|---|
| Suggestive | Mild (require explanation) | **Direct** — phrase literally describes what users do with the product |
| Memorable | 3-syllable invented, decent | **Iconic** — one of the most-quoted lines in tech-cinema history |
| Imagery | Abstract | **Visual** — Neo in the chair, eyes opening, the realization |
| Legs | Limited story | **Massive** — *"For your agents."* / *"Show me."* / `kfu install` / Matrix-adjacent (but not Matrix-iconography-derivative) ecosystem |
| Emotional | Mild | **Strong** — the *"I know kung fu"* moment is a near-universal "aha" for the dev demographic |

The trade-offs:

- **CLI ergonomics**: 11-character name is too long. → Mitigated with `kfu` short alias (`[project.scripts]` entry).
- **Generational skew**: under-30 devs may need to Google the reference. → Acceptable; the buying audience for serious skill-registries skews 35+ (senior engineers, tech leads, platform engineers).
- **Trademark risk**: low. The phrase itself is too short to be trademarkable as dialogue. Warner Bros owns *The Matrix* film copyright and the "THE MATRIX" mark, but not individual lines. Mitigation: avoid Matrix iconography, optionally $300-500 USPTO clearance consult before public launch.
- **Aging**: every year the reference is older. → Accepted; *Jekyll* names itself after an 1886 novel and has aged fine. References age into wisdom in tech naming.

The fallback list (Aurika, Korva, Evria) remains documented and can be activated if `I Know Kung Fu` faces a problem we haven't anticipated. Evria has a known flaw: pronunciation ambiguity in Italian (ev-RI-a vs É-vria). Korva is the strongest pure-coined backup; Aurika the strongest Italian-lyrical backup.

---

## 6. What we learned about 2026 AI/agent naming (for future projects)

Generalizable findings beyond this specific decision:

1. **Every short English noun ≤6 letters is PyPI-squatted.** Probing rate confirmed: 100% of 13 playful nouns tested were taken; ~95% of evocative English words tested were taken.
2. **The `skill*` and `agent*` namespaces are exhausted** in mid-2026. 15+ direct competitors exist. Any name in this conceptual bin will be Copycat-flagged.
3. **Coined / invented names are the only category with reliable available namespace.** ~40% of probed coined candidates were clean across PyPI + brand.
4. **Cultural-reference phrases (4-5 words) escape squatting** because squatters don't claim multi-word phrases. Trade-off: longer at the install command, but CLI aliases solve this.
5. **Brand-adjacent phonetic neighbors matter as much as exact matches.** Oreka was killed by Orkes ($60M Series B for AI agent orchestration) despite being a different spelling. Said aloud, Orkes and Oreka are confusable.
6. **PyPI free ≠ name viable.** A name can be PyPI-free but still strategically dead if a competitor in your space owns a phonetic neighbor.

---

## 7. Immediate next actions (Phase 2 follow-on)

These should be done in the next 24 hours to prevent squatter capture now that the name has been published in this conversation:

- [ ] Register `iknowkungfu.io` and `iknowkungfu.ai` (cheap, prevents squatters)
- [ ] Defensively register `iknowkungfu.com` and `iknowkungfu.dev` if budget allows
- [ ] **Reserve PyPI** by publishing `iknowkungfu==0.0.0` placeholder
- [ ] **Reserve GitHub org** `iknowkungfu` (if available — currently using `samuelgudi/iknowkungfu`)
- [ ] **Reserve Twitter / X / Bluesky** handles `iknowkungfu`
- [ ] Optional: $300-500 USPTO trademark clearance consult

Then the session-6 plan resumes (Phase 1 rename in codebase, bump 0.1.2, ship to PyPI, make repo public, announce).

---

## 8. Cross-references

- `docs/decisions.md` § ADR-001 — the locked decision
- `docs/handoff/2026-05-12-execution-handoff-session6.md` — the prior session plan, which assumed a rename was needed but did not specify the name
- `docs/handoff/2026-05-12-execution-handoff-session5.md` — session-5 close-out, which identified the strategic naming problem

End of naming-decision record.
