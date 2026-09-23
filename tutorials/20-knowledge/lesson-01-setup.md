# Lesson 1 — Setup and the mental model

The hub is not a wiki. It is a **container** that holds multiple independent
wikis (called topics) plus indexes and a log that covers all of them.

## What the hub contains

```
~/.local/share/llm-wiki/
├── wikis.json              # registry of all topics
├── _index.md               # derived: master topic list
├── log.md                  # append-only: every action
└── topics/
    ├── climate-science/    # one topic
    ├── kubernetes/         # another topic
    └── typescript-async/   # third topic
```

The top three files are **hub-level metadata**. Everything else is **topic
content**. The separation matters: you can delete a topic without touching the
hub's integrity, and you can sync the hub across machines without syncing every
topic.

## Initialization

```bash
/wiki init climate-science
```

This creates the hub (if missing) and the first topic. It does not prompt for
anything — the topic name is mandatory. If you run `init` again with a
different topic name, it creates a second topic in the same hub.

## Resolution order

Every command that needs a hub follows this precedence:

1. Read `~/.config/llm-wiki/config.json`, field `hub_path` if present
2. Else read `$HOME/wiki/_index.md` (the default location)
3. Else ask the user (never assume)

If you have multiple machines or workflows, you can point to different hubs by
setting `config.json`. The default is a single personal hub at `~/wiki/`.

## The critical allowlist: before lesson 2

When you run `/wiki:research` in the next lesson, it will invoke `WebFetch`
(to download URLs) and `WebSearch` (to find sources). Unless these are
allowlisted in your settings, you will see a permission prompt for **every**
source — often 20–40 per run.

Allowlist them now:

```bash
# Edit .claude/settings.local.json
# Add or merge into the "allow" block:

"allow": [
  "WebFetch",
  "WebSearch"
]
```

This is a one-time setup. Once set, research runs proceed without pausing.

## Verify the setup

```bash
# Check that the hub exists
ls -la ~/.local/share/llm-wiki/

# Check that the default config resolves
cat ~/.config/llm-wiki/config.json
```

If you get "file not found" on the second command, the hub is using the
fallback `~/wiki/_index.md` location, which is fine.

---

Next: [Lesson 2 — One command: /wiki:research](lesson-02-one-command.md)
