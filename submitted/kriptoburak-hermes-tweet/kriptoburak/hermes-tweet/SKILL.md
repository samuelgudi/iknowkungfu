---
name: hermes-tweet
description: |
  Use this skill when a Hermes Agent needs X/Twitter automation through Hermes Tweet: search tweets, read replies, look up users, export followers, monitor tweets, post tweets or replies, send DMs, and manage approval-gated X actions via Xquik.
---

# Hermes Tweet

Hermes Tweet is the native Hermes Agent plugin for X/Twitter automation through Xquik. Use it when a Hermes session needs structured tools for tweet search, reply reading, user lookup, follower export, tweet monitoring, X trends, posting, replies, DMs, media, extraction jobs, webhooks, or other approval-gated X actions.

## When to use

Use this skill when the user asks for any of these workflows from Hermes Agent:

- Search Twitter/X or scrape/search tweets with query operators.
- Read tweet replies, quote tweets, threads, bookmarks, lists, or community tweets.
- Look up X users, inspect profiles, search accounts, or export followers.
- Monitor tweets, accounts, keywords, trends, or webhook events.
- Download tweet media or run extraction jobs.
- Post tweets, send replies, like, retweet, follow, unfollow, remove followers, or send DMs after explicit approval.
- Install or verify a Hermes Agent X/Twitter plugin.

Do not use this skill for generic web search, non-X social networks, or raw credential collection.

## Install

Install and enable the Hermes plugin:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

Install the published Python package into the Hermes Python environment:

```bash
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hermes-tweet
hermes plugins enable hermes-tweet
```

If `uv` is not available but the Hermes venv includes `pip`, use:

```bash
~/.hermes/hermes-agent/venv/bin/python -m pip install hermes-tweet
hermes plugins enable hermes-tweet
```

Set the Xquik API key in the Hermes runtime environment, not in chat:

```bash
export XQUIK_API_KEY="xq_..."
export HERMES_TWEET_ENABLE_ACTIONS="false"
```

`HERMES_TWEET_ENABLE_ACTIONS=false` is the safe default. Turn it on only for sessions with explicit approval gates for posting, replies, DMs, follows, monitor changes, webhook changes, extraction jobs, or other account actions.

## Tool workflow

Hermes Tweet exposes three tools:

| Tool | Use |
| --- | --- |
| `tweet_explore` | Search the bundled Xquik endpoint catalog. Does not call the API. |
| `tweet_read` | Call catalog-listed read-only endpoints. |
| `tweet_action` | Call write-like or private endpoints when action gating is enabled. |

Always start with `tweet_explore` unless the exact endpoint is already known from the catalog.

## Decision rules

- If the user asks what is possible, call `tweet_explore` with a short capability query.
- If the endpoint method is `GET` and the catalog does not mark it as an action, call `tweet_read`.
- If the endpoint is write-like, private, mutating, or monitor/webhook/extraction related, call `tweet_action` only after the user approves the exact operation.
- If `tweet_action` is unavailable, explain that action tools are intentionally gated by `HERMES_TWEET_ENABLE_ACTIONS=true`.
- If `XQUIK_API_KEY` is missing, ask the user to configure it in the Hermes runtime environment. Do not ask them to paste the key in chat.

## Common endpoint searches

Use these `tweet_explore` query patterns:

```json
{"query":"search tweets","method":"GET"}
```

```json
{"query":"read tweet replies","method":"GET"}
```

```json
{"query":"look up users","method":"GET"}
```

```json
{"query":"export followers","method":"GET"}
```

```json
{"query":"monitor tweets","include_actions":true}
```

```json
{"query":"post tweet","include_actions":true}
```

```json
{"query":"send direct message","include_actions":true}
```

## Example read calls

Search tweets:

```json
{"path":"/api/v1/x/tweets/search","query":{"q":"AI agents","limit":25}}
```

Read replies:

```json
{"path":"/api/v1/x/tweets/1234567890/replies","query":{}}
```

Search users:

```json
{"path":"/api/v1/x/users/search","query":{"q":"open source agents"}}
```

Export followers:

```json
{"path":"/api/v1/x/users/123456789/followers","query":{"pageSize":100}}
```

## Example action calls

Before every `tweet_action`, state the endpoint, method, and payload. Continue only after explicit approval.

Create a monitor:

```json
{"path":"/api/v1/monitors","method":"POST","body":{"username":"example","eventTypes":["tweet.new","tweet.reply"]},"reason":"Create the user-approved X monitor."}
```

Post a tweet:

```json
{"path":"/api/v1/x/tweets","method":"POST","body":{"account":"@example","text":"Approved tweet text"},"reason":"Post the user-approved tweet."}
```

Send a DM:

```json
{"path":"/api/v1/x/dm/123456789","method":"POST","body":{"account":"@example","text":"Approved DM text"},"reason":"Send the user-approved DM."}
```

## Safety

- Never ask for or reveal API keys, passwords, cookies, TOTP secrets, or session tokens.
- Never pass credentials in tool arguments, examples, issue bodies, logs, or prompts.
- Prefer read-only calls for social listening, tweet search, reply reading, user lookup, follower export, and trend research.
- Require explicit approval before posting tweets, replying, sending DMs, following, unfollowing, deleting, changing monitors, creating webhooks, or running extraction jobs.
- Do not use account connection, re-authentication, API-key management, billing, credit top-up, or support-ticket endpoints.
- Do not guess endpoint paths. Search the catalog with `tweet_explore`.
- Do not retry writes through alternate routes after a policy, auth, or account-state error.

## Verification

After install:

```bash
hermes tools list
```

Expected:

- The `hermes-tweet` toolset is enabled.
- `tweet_explore` is available without `XQUIK_API_KEY`.
- `tweet_read` appears when `XQUIK_API_KEY` is configured.
- `tweet_action` stays hidden or disabled unless `HERMES_TWEET_ENABLE_ACTIONS=true`.

## References

- Hermes Tweet repository: https://github.com/Xquik-dev/hermes-tweet
- Hermes Tweet guide: https://docs.xquik.com/guides/hermes-tweet
- PyPI package: https://pypi.org/project/hermes-tweet/
