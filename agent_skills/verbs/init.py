"""init verb — scaffold meta.json interactively from SKILL.md."""
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ── Constants ─────────────────────────────────────────────────────────────────

CATEGORIES = ["media", "dev", "ops", "data", "comms", "docs", "meta", "ai"]

AGENTS = ["claude-code", "hermes", "codex", "opencode", "pi", "openclaw"]

COMMAND_TOKENS = {
    "ssh", "git", "curl", "wget", "docker", "kubectl", "aws", "gcloud",
    "az", "npm", "pip", "node", "python", "python3", "make", "cargo",
    "go", "rustup", "yarn", "pnpm", "ffmpeg", "rsync", "scp", "tar",
    "zip", "unzip", "jq", "yq", "sed", "awk", "grep",
}

# Real env-var USES, not bare acronyms. Patterns:
#   $VAR / ${VAR}               (shell)
#   os.environ[X] / .get(X)     (Python dict-style and method-style)
#   os.getenv(X)                (Python)
# Captures the variable name itself.
ENV_VAR_PATTERNS = [
    re.compile(r"\$\{?([A-Z_][A-Z0-9_]*)\}?"),
    re.compile(r"os\.environ(?:\[|\.get\(\s*)[\"']([A-Z_][A-Z0-9_]*)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, text

    fm_text = "".join(lines[1:end])
    body = "".join(lines[end + 1:])

    if yaml is not None:
        try:
            fm = yaml.safe_load(fm_text) or {}
        except Exception:
            fm = {}
    else:
        # Minimal key: value parser (no nesting needed for name/description)
        fm = {}
        for line in fm_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()

    return fm, body


def _scan_body(body: str) -> tuple[list[str], list[str]]:
    """Scan body text for env-var USES (not bare ALL_CAPS acronyms) and
    command tokens. Pre-Finding-8a, the env-var heuristic was a bare
    `\\b[A-Z][A-Z0-9_]{2,}\\b` regex which matched any prose acronym
    (SSH, LLM, NFS) — high false-positive rate. Now patterns require an
    actual use site: $VAR, ${VAR}, os.environ[...], os.getenv(...)."""
    env_vars: list[str] = []
    seen_env: set[str] = set()
    for pat in ENV_VAR_PATTERNS:
        for m in pat.finditer(body):
            tok = m.group(1)
            if tok and tok not in seen_env:
                env_vars.append(tok)
                seen_env.add(tok)

    # commands unchanged
    commands = []
    seen_cmd: set[str] = set()
    for token in COMMAND_TOKENS:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, body) and token not in seen_cmd:
            commands.append(token)
            seen_cmd.add(token)
    commands.sort()
    return env_vars, commands


def _prompt(prompt_text: str, default: str = "") -> str:
    """Print a prompt and read a line from stdin. Falls back to default on empty."""
    display = f"{prompt_text} [{default}]: " if default else f"{prompt_text}: "
    try:
        val = input(display).strip()
    except EOFError:
        val = ""
    return val if val else default


def _fetch_gh_user() -> tuple[str, int]:
    """Call `gh api user` and return (login, id). Raises on failure."""
    try:
        result = subprocess.run(
            ["gh", "api", "user"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError("gh not found. Install GitHub CLI and run `gh auth login` first.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"gh api user failed (exit {e.returncode}). Run `gh auth login` first.\n{e.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
        return str(data["login"]), int(data["id"])
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Unexpected response from gh api user: {e}\n{result.stdout[:200]}")


# ── Main entry ────────────────────────────────────────────────────────────────

def run(args) -> int:
    target = Path(args.target).resolve()

    # ── Step 1: detect SKILL.md ───────────────────────────────────────────────
    # Use os.listdir to get exact filenames (case-sensitive, even on Windows).
    import os
    try:
        actual_names = set(os.listdir(target))
    except OSError as e:
        print(f"Error: cannot read directory {target}: {e}", file=sys.stderr)
        return 1

    upper = target / "SKILL.md"
    lower = target / "skill.md"
    has_upper = "SKILL.md" in actual_names
    has_lower = "skill.md" in actual_names

    if has_upper and has_lower:
        print(
            f"Error: both SKILL.md and skill.md exist in {target}. "
            "Remove or merge the conflicting file.",
            file=sys.stderr,
        )
        return 1

    if not has_upper and not has_lower:
        print(
            f"Error: no SKILL.md found in {target}.\n"
            "An `agent-skills` skill needs a `SKILL.md` with frontmatter.",
            file=sys.stderr,
        )
        return 1

    if has_lower and not has_upper:
        lower.rename(upper)
        print(f"  Renamed skill.md → SKILL.md")

    skill_md_path = upper

    # ── Step 2: parse frontmatter ─────────────────────────────────────────────
    text = skill_md_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    name = fm.get("name", "")
    description = fm.get("description", "")

    if not name:
        print("Error: SKILL.md frontmatter is missing required field: name", file=sys.stderr)
        return 1
    if not description:
        print("Error: SKILL.md frontmatter is missing required field: description", file=sys.stderr)
        return 1

    print(f"\nReading {skill_md_path}…")
    print(f"  Frontmatter parsed: name={name}, description={len(description)} chars")

    # ── Step 3: GitHub user ───────────────────────────────────────────────────
    try:
        gh_login, gh_id = _fetch_gh_user()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"\n  GitHub handle (detected via gh): {gh_login}")
    print(f"  GitHub user ID (fetched from gh api): {gh_id}")

    # ── Step 4: body scanning ─────────────────────────────────────────────────
    detected_env, detected_cmds = _scan_body(body)

    print()
    if detected_env:
        print(f"  Detected env vars: {detected_env}")
    else:
        print("  Scanning SKILL.md for env-var-shaped names… none detected. requires.env_vars = []")

    if detected_cmds:
        print(f"  Detected commands: {detected_cmds}")
    else:
        print("  Scanning SKILL.md for shell-command patterns… none detected.")

    # ── Step 5: interactive prompts ───────────────────────────────────────────
    # Default id slug comes from SKILL.md frontmatter `name` (source of truth),
    # not from `target.name` — the dir is incidental, the frontmatter is
    # canonical. Falls back to target.name only if frontmatter parsing failed
    # somehow (defensive; the missing-name case already exits earlier).
    slug = name or target.name
    default_id = f"{gh_login}/{slug}"

    print()
    skill_id = _prompt("  id", default_id)
    version = _prompt("  version", "0.1.0")
    status = _prompt("  status", "active")
    license_ = _prompt("  license", "MIT")

    # Category
    print("\n  Category? Pick one:")
    cat_line = "    " + "  ".join(f"[{i+1}] {c}" for i, c in enumerate(CATEGORIES))
    print(cat_line)
    cat_sel_raw = _prompt("  Selection", "1")
    try:
        cat_idx = int(cat_sel_raw.strip()) - 1
        if not 0 <= cat_idx < len(CATEGORIES):
            raise ValueError
        category = CATEGORIES[cat_idx]
    except (ValueError, IndexError):
        print(f"Invalid category selection '{cat_sel_raw}'. Defaulting to '{CATEGORIES[0]}'.")
        category = CATEGORIES[0]

    # Tags
    tags_raw = _prompt("  Tags (comma-separated, max 10)", "")
    tags = [t.strip().lower() for t in tags_raw.split(",") if t.strip()][:10]

    # Platforms
    platforms_raw = _prompt("  Platforms", "linux,macos,windows")
    platforms = [p.strip() for p in platforms_raw.split(",") if p.strip()]

    # Agent compat
    print("\n  Agent compatibility? (toggle with number, enter to confirm)")
    for i, a in enumerate(AGENTS):
        print(f"    [{i+1}] {a}")
    agents_raw = _prompt("  Selection (CSV)", "1")
    agent_compat = []
    for part in agents_raw.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(AGENTS):
                agent_compat.append(AGENTS[idx])
        except (ValueError, IndexError):
            pass
    if not agent_compat:
        agent_compat = ["claude-code"]

    # Commands
    cmd_default = ",".join(detected_cmds) if detected_cmds else ""
    cmds_raw = _prompt(
        f"  requires.commands (CSV{'; detected: ' + ','.join(detected_cmds) if detected_cmds else ''})",
        cmd_default,
    )
    commands = [c.strip() for c in cmds_raw.split(",") if c.strip()]

    # Env vars
    env_default = ",".join(detected_env) if detected_env else ""
    env_raw = _prompt(
        f"  requires.env_vars (CSV{'; detected: ' + ','.join(detected_env) if detected_env else ''})",
        env_default,
    )
    env_vars = [e.strip() for e in env_raw.split(",") if e.strip()]

    # ── Step 6: build install map ─────────────────────────────────────────────
    install: dict = {}
    for agent in agent_compat:
        if agent == "claude-code":
            install[agent] = {"scope": "user"}
        else:
            install[agent] = {}

    # ── Step 7: write meta.json ───────────────────────────────────────────────
    meta = {
        "id": skill_id,
        "version": version,
        "status": status,
        "author": {
            "name": gh_login,
            "github_login": gh_login,
            "github_id": gh_id,
        },
        "category": category,
        "tags": tags,
        "platforms": platforms,
        "agent_compat": agent_compat,
        "requires": {
            "env_vars": env_vars,
            "commands": commands,
        },
        "license": license_,
        "install": install,
        "composes": [],
        "extends": None,
        "supersedes": [],
        "superseded_by": None,
        "related_skills": [],
    }

    meta_path = target / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\nWriting {meta_path}…")
    print(f"  ✓ id={skill_id}, version={version}, status={status}, license={license_}")
    print(f"  ✓ category={category}, tags={tags}, platforms={platforms}, agent_compat={agent_compat}")
    print(f"  ✓ requires.env_vars={env_vars}, requires.commands={commands}")
    print("  ✓ Reserved fields (composes/extends/supersedes/superseded_by) initialized empty")
    print(f"\nDone. Review with:\n  cat {meta_path}")
    print(f"\nNext:\n  agent-skills submit {target}")

    return 0
