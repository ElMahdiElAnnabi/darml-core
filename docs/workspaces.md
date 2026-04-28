# Workspaces (Pro Team)

A workspace is a billing + access boundary for teams. One Stripe
subscription, multiple users, shared build cache, audit log of who
built what.

## Quick concepts

| | |
|---|---|
| **Workspace** | The team. Has a slug (URL-safe), name, owner, and tier. |
| **Member** | A user who can build against the workspace's quota. |
| **Role** | `owner` (created it, owns billing), `admin` (manages members), `member` (builds and reads audit). |
| **Slug** | 3–40 chars, lowercase alphanumeric or dash, can't start/end with dash. URL-visible. Choose carefully — not currently renameable. |
| **Quota scope** | Workspace tier defines the monthly hosted-build limit. Members consume against it; one rogue script can spend the team's pool. (Per-member sub-quotas: planned, not yet shipped.) |
| **Cache scope** | Within a workspace, members share build-cache hits. Across workspaces and personal keys, caches are isolated. |

## Create a workspace

You need a Pro Cloud (or higher) API key.

```bash
export DARML_API_KEY=sk_pro_…
curl -X POST https://api.darml.dev/v1/workspaces \
  -H "X-API-Key: $DARML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"slug": "acme-platform", "name": "Acme Platform Team"}'
```

You're automatically the owner. Workspace tier starts as `free_signup`
(30 hosted builds/month). Upgrade by purchasing Pro Team (€99/mo) —
the Stripe subscription auto-attaches to the workspace whose slug you
pass during checkout.

## Invite a teammate

```bash
curl -X POST https://api.darml.dev/v1/workspaces/acme-platform/members \
  -H "X-API-Key: $DARML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_email": "alice@acme.com", "role": "member"}'
```

Roles:
- `member` — can build, read members list, read audit log
- `admin` — `member` + can invite, remove (non-owner), see denied attempts
- `owner` — `admin` + can archive, transfer ownership

Only owners and admins can invite. Members get a 403 if they try.

## Accept an invite

The invited user verifies with their own API key (you can mint them one
through the dashboard before they accept):

```bash
export DARML_API_KEY=alice_sk_pro_…
curl -X POST \
  https://api.darml.dev/v1/workspaces/acme-platform/members/alice@acme.com/accept \
  -H "X-API-Key: $DARML_API_KEY"
```

A user can ONLY accept their own invite — owner cannot accept on a
member's behalf. After accept, the workspace shows up in the user's
`GET /v1/workspaces` list.

## Read the audit log

Owners, admins, and members can all read. Returns the most recent
events first, newest 100 by default.

```bash
curl https://api.darml.dev/v1/workspaces/acme-platform/audit \
  -H "X-API-Key: $DARML_API_KEY"
```

Sample output:

```json
[
  {"action": "permission.denied", "actor_email": "intern@acme.com",
   "target": "required=owner,admin;actual=member", "created_at": 1777400000},
  {"action": "member.invite", "actor_email": "owner@acme.com",
   "target": "alice@acme.com", "created_at": 1777395000},
  {"action": "workspace.create", "actor_email": "owner@acme.com",
   "target": "acme-platform", "created_at": 1777390000}
]
```

Both successful actions and denied attempts are logged. The log is
append-only — no application code path UPDATEs or DELETEs from it
(verified by `tests/security/test_audit_log_append_only.py`).

## Transfer ownership

Owner only. Target must already be an accepted member.

```bash
curl -X POST \
  https://api.darml.dev/v1/workspaces/acme-platform/transfer \
  -H "X-API-Key: $DARML_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"new_owner_email": "alice@acme.com"}'
```

After transfer, the previous owner becomes an admin and can either
stay around or remove themselves via `DELETE
/v1/workspaces/{slug}/members/{email}`.

## Archive (delete) a workspace

Owner only. Soft-delete — the workspace stops appearing in lists, the
shared cache stops returning hits, but member API keys keep working
under their personal tier.

```bash
curl -X DELETE https://api.darml.dev/v1/workspaces/acme-platform \
  -H "X-API-Key: $DARML_API_KEY"
```

Restore is currently a manual database operation; reach out to
support@darml.dev if you need it back.

## Workspace switching in the CLI

Currently the CLI uses your API key directly; the workspace is implied
by which key you set in `DARML_API_KEY`. To switch workspaces, set a
different key. Future versions will support `darml use <slug>` to
switch the active workspace within a single key when one user belongs
to multiple workspaces.

## Known v1 limits

- **Per-member sub-quotas**: not yet implemented. A rogue script in one
  member's CI can burn the whole workspace's monthly quota. Coming.
- **Slug renaming**: not supported. Pick carefully on creation.
- **Email-link invites**: today an invite is a DB row keyed by user
  email; the user accepts via API call. We don't yet send a
  signed-link email automatically (Stripe-style "click here to join").
- **Workspace restore**: manual DB operation only.

These are in the backlog and will land as customer demand surfaces.
