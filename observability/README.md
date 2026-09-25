# observability/

Health snapshots of this repo's harness, written by the
[ai-literacy-superpowers](https://github.com/Habitat-Thinking/ai-literacy-superpowers)
plugin's `/harness-health` command. [`HARNESS.md`](../HARNESS.md) declares
what is checked; each snapshot records how those checks stood on its date.

| path | what |
|---|---|
| `snapshots/YYYY-MM-DD-snapshot.md` | one snapshot per run; the README's Harness Health badge links to the latest |
| `archive/` | snapshots older than six months, moved by the "Observability archive" GC rule (does not exist yet) |

Snapshots are compared with each other to find trends, so do not edit an old
one. Take a new snapshot instead.

`affordance-invocations.json` is a log that a plugin hook writes locally. It
contains the session id, so it is gitignored. Never commit it.
