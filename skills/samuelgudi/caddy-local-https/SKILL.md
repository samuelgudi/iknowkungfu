---
name: caddy-local-https
description: Use this skill when setting up local development services behind clean HTTPS hostnames using Caddy as a reverse proxy. Covers .localhost domains, Caddy's internal CA, path-based routing to multiple backends, and the common port-443 and certificate pitfalls.
---

# caddy-local-https

Local development usually means a pile of `localhost:3000`, `localhost:8000`, `localhost:8100` URLs — easy to mix up, no HTTPS, and cookies/CORS/service-worker behaviour that does not match production. Caddy fixes this with a few lines of config: real hostnames, automatic HTTPS, one front door for several backends.

## Use this skill when

- You are running two or more local services and want to reach them by name instead of by port.
- You need HTTPS locally because the app's behaviour depends on it (secure cookies, service workers, `SameSite`, OAuth redirect URIs).
- You want one hostname to route to several backends by path (`/api/*` to one service, everything else to another).

## Why `.localhost` and Caddy's internal CA

- The `.localhost` TLD always resolves to the loopback address — no `hosts` file editing, no DNS setup. `myapp.localhost` just works.
- Caddy ships an **internal CA**. For `.localhost` (and other internal names) it issues its own certificates automatically and, on first run, offers to install its root into the system trust store. Once trusted, `https://myapp.localhost` is green in the browser with zero per-site certificate work.
- This is for **local development only**. Caddy's internal CA is not trusted by anyone else's machine. For a public-facing site Caddy does real ACME/Let's Encrypt issuance instead — different mode, not what this skill covers.

## Minimal Caddyfile — one hostname, one backend

```caddy
myapp.localhost {
	reverse_proxy 127.0.0.1:3000
}
```

That is the whole file. `caddy run --config ./Caddyfile` (or `caddy reload` if it is already running) and `https://myapp.localhost` proxies to your app on port 3000, with HTTPS terminated by Caddy.

## Path-based routing — one hostname, several backends

When a single app is really a frontend plus an API plus another service, route by path with `handle` blocks:

```caddy
myapp.localhost {
	handle /api/* {
		reverse_proxy 127.0.0.1:8000
	}
	handle /embedding/* {
		reverse_proxy 127.0.0.1:8100
	}
	handle {
		reverse_proxy 127.0.0.1:3000
	}
}
```

`handle` blocks are **mutually exclusive** and evaluated in order — the first match wins, and the bare `handle` at the end is the catch-all. This matters: a bare `handle` placed *first* would swallow every request. Put the specific paths first, the catch-all last.

If a backend expects to receive requests *without* the path prefix, strip it:

```caddy
	handle /api/* {
		uri strip_prefix /api
		reverse_proxy 127.0.0.1:8000
	}
```

## The pitfalls

- **Port 443 needs elevation.** Caddy binds `:443` for HTTPS, and binding a port below 1024 is privileged: administrator on Windows, root or `setcap cap_net_bind_service` on Linux. If Caddy starts but no site is reachable, this is the first thing to check. When Caddy runs as a service, make sure that service runs elevated.
- **Do not "fix" it by switching to `http://`.** Dropping to plain HTTP makes the error go away but also removes the thing you set this up for — local behaviour stops matching production. Solve the elevation problem instead.
- **Trust the root CA once.** If the browser warns about the certificate, Caddy's root has not been installed into the system trust store. Install it once (Caddy does this on first run if it has the permissions); after that every `.localhost` site is trusted.
- **`reload`, do not restart, for config changes.** `caddy reload --config <path>` applies a new Caddyfile with zero downtime. Restarting drops connections for no reason.
- **One Caddy instance owns `:443`.** Two Caddy processes, or Caddy plus another local TLS terminator, will fight over the port. Run one.

## Anti-patterns

- **A bare `handle` before specific paths.** It is the catch-all; anything after it is dead config. Specific first, catch-all last.
- **Editing the `hosts` file for `.localhost` names.** Unnecessary — `.localhost` already resolves to loopback. Reserve `hosts` edits for non-`.localhost` names.
- **Committing a Caddyfile full of machine-specific absolute paths.** Keep the Caddyfile portable; if a path must be absolute, make it configurable rather than hard-coded to one developer's machine.
- **Reaching for `http://` the moment HTTPS is inconvenient.** The whole point was production-like local behaviour.

## What this skill does not do

- It does not cover production TLS (real ACME/Let's Encrypt issuance, public domains) — that is a different Caddy mode.
- It does not install Caddy. Caddy must already be on `PATH`.
- It does not cover Caddy's other features (static file serving, auth, rate limiting, request rewriting beyond `strip_prefix`) — only the reverse-proxy-for-local-dev case.
