from clients.skill_discovery.match import score, rank

REGISTRY = {
    "schema_version": 2,
    "skills": [
        {"id": "a/spotify-search", "name": "spotify-search",
         "description": "Search Spotify by track or artist.",
         "tags": ["spotify", "music"], "version": "0.1.0",
         "agent_compat": ["claude-code"], "category": "media",
         "status": "active", "platforms": ["linux"], "has_scripts": True},
        {"id": "a/lastfm", "name": "lastfm",
         "description": "Last.fm music lookup.",
         "tags": ["lastfm", "music"], "version": "0.2.0",
         "agent_compat": ["claude-code"], "category": "media",
         "status": "active", "platforms": ["linux"], "has_scripts": False},
    ],
}


def test_exact_match_scores_higher():
    candidates = rank("spotify", REGISTRY, agent="claude-code", limit=2)
    assert candidates[0]["id"] == "a/spotify-search"


def test_filter_agent_drops_incompatible():
    skills_with_other = dict(REGISTRY)
    skills_with_other["skills"] = REGISTRY["skills"] + [
        {**REGISTRY["skills"][0], "id": "z/hermes-only", "agent_compat": ["hermes"]}
    ]
    candidates = rank("spotify", skills_with_other, agent="claude-code", limit=10)
    assert all("hermes-only" not in c["id"] for c in candidates)


def test_deprecated_excluded_by_default():
    reg = dict(REGISTRY)
    reg["skills"] = REGISTRY["skills"] + [
        {**REGISTRY["skills"][0], "id": "a/old", "status": "deprecated"}
    ]
    candidates = rank("spotify", reg, agent="claude-code", limit=10)
    assert all("/old" not in c["id"] for c in candidates)


def test_regex_chars_in_query_dont_crash():
    candidates = rank("spotify[*]", REGISTRY, agent="claude-code", limit=2)
    assert isinstance(candidates, list)


def test_filter_by_category():
    reg = {
        "schema_version": 2,
        "skills": REGISTRY["skills"] + [
            {"id": "b/gh-search", "name": "gh-search",
             "description": "Search GitHub repositories.",
             "tags": ["github", "code"], "version": "0.1.0",
             "agent_compat": ["claude-code"], "category": "dev",
             "status": "active", "platforms": ["linux"], "has_scripts": False},
        ],
    }
    candidates = rank("search", reg, agent="claude-code", category="media", limit=10)
    assert all(c["category"] == "media" for c in candidates)
    ids = {c["id"] for c in candidates}
    assert "b/gh-search" not in ids


def test_filter_by_tag():
    reg = {
        "schema_version": 2,
        "skills": REGISTRY["skills"] + [
            {"id": "c/weather", "name": "weather",
             "description": "Get current weather data.",
             "tags": ["weather", "api"], "version": "0.1.0",
             "agent_compat": ["claude-code"], "category": "data",
             "status": "active", "platforms": ["linux"], "has_scripts": False},
        ],
    }
    candidates = rank("music", reg, agent="claude-code", tag="music", limit=10)
    assert all("music" in c["tags"] for c in candidates)
    ids = {c["id"] for c in candidates}
    assert "c/weather" not in ids


def test_yanked_version_excluded():
    reg = {
        "schema_version": 2,
        "skills": REGISTRY["skills"] + [
            {"id": "a/yanked-skill", "name": "yanked-skill",
             "description": "Search Spotify plus extra features.",
             "tags": ["spotify", "music"], "version": "0.1.0",
             "agent_compat": ["claude-code"], "category": "media",
             "status": "active", "platforms": ["linux"], "has_scripts": False,
             "versions": {"0.1.0": {"yanked": True}}},
        ],
    }
    candidates = rank("spotify", reg, agent="claude-code", limit=10)
    assert all("yanked-skill" not in c["id"] for c in candidates)


def test_deprecated_included_when_include_archived():
    reg = dict(REGISTRY)
    reg["skills"] = REGISTRY["skills"] + [
        {**REGISTRY["skills"][0], "id": "a/old-archived", "status": "deprecated"}
    ]
    candidates = rank("spotify", reg, agent="claude-code", limit=10, include_archived=True)
    ids = {c["id"] for c in candidates}
    assert "a/old-archived" in ids


def test_limit_respected():
    candidates = rank("music", REGISTRY, agent="claude-code", limit=1)
    assert len(candidates) <= 1


def test_score_field_present_in_results():
    candidates = rank("spotify", REGISTRY, agent="claude-code", limit=2)
    for c in candidates:
        assert "score" in c
        assert isinstance(c["score"], float)


def test_filter_by_platform():
    reg = {
        "schema_version": 2,
        "skills": REGISTRY["skills"] + [
            {"id": "d/win-skill", "name": "win-skill",
             "description": "A Windows-only music skill.",
             "tags": ["music"], "version": "0.1.0",
             "agent_compat": ["claude-code"], "category": "media",
             "status": "active", "platforms": ["windows"], "has_scripts": False},
        ],
    }
    candidates = rank("music", reg, agent="claude-code", platform="linux", limit=10)
    assert all("linux" in c["platforms"] for c in candidates)
    ids = {c["id"] for c in candidates}
    assert "d/win-skill" not in ids
