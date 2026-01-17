# AIO Context Pack Management Skill

This skill helps manage context packs in the AIorgianization system. Context packs are reusable knowledge documents that provide background information for AI assistance, eliminating the need to re-explain context in every conversation.

## Context Pack Types

- **Domains** (`domain`): Business domain knowledge (e.g., Payments, Identity, Compliance)
- **Systems** (`system`): Technical system documentation (e.g., Payment-API, Auth-Service)
- **Operating** (`operating`): Processes and procedures (e.g., Definition-of-Done, Ticket-Standards)

## Available Tools

### Reading Context
- `aio_get_context(packs: ["name1", "name2"])` - Get content from context packs
- `aio_list_context_packs(category?: "domain"|"system"|"operating")` - List available packs

### Adding Information
- `aio_add_to_context_pack(pack, content, section?)` - Add text content to existing pack
- `aio_add_file_to_context_pack(pack, file, section?)` - Copy file contents into pack
- `aio_create_context_pack(title, category, content?, description?, tags?)` - Create new pack

## When to Use

### Adding to Existing Pack

When the user says things like:
- "Add this to my payments context"
- "Update the auth-service pack with this info"
- "Include this in the definition of done"
- "Save this to context: [topic]"

Use `aio_add_to_context_pack`:
```json
{
  "pack": "payments",
  "content": "## PCI Compliance\n\nAll payment data must be encrypted at rest...",
  "section": "Compliance"
}
```

### Adding Files to Packs

When the user says things like:
- "Add this ADR to my payments context"
- "Include the migration doc in the system pack"
- "Copy the runbook to the operating context"

Use `aio_add_file_to_context_pack`:
```json
{
  "pack": "payments",
  "file": "ADRs/2024-01-payment-provider.md",
  "section": "References"
}
```

### Creating New Packs

When the user says things like:
- "Create a context pack for the new billing system"
- "Start a new operating context for code review standards"
- "I need a domain context for the identity project"

Use `aio_create_context_pack`:
```json
{
  "title": "Billing System",
  "category": "system",
  "content": "## Overview\n\nThe billing system handles...",
  "description": "Technical context for the billing microservice",
  "tags": ["billing", "payments", "subscriptions"]
}
```

### Listing Available Packs

When unsure which pack to use, or when the user asks:
- "What context packs do I have?"
- "Show me my domain packs"
- "List all context packs"

Use `aio_list_context_packs`:
```json
{ "category": "domain" }
```

## Natural Language Patterns

| User Says | Action |
|-----------|--------|
| "add to my {topic} context" | `aio_add_to_context_pack(pack=topic, ...)` |
| "update the {name} pack" | `aio_add_to_context_pack(pack=name, ...)` |
| "add this file to {pack}" | `aio_add_file_to_context_pack(pack, file)` |
| "save this to {category} context: {title}" | May create or append based on existence |
| "what context packs do I have?" | `aio_list_context_packs()` |
| "create a new {category} pack for {title}" | `aio_create_context_pack(...)` |

## Best Practices

1. **Check before creating**: Use `aio_list_context_packs` to see if a pack already exists before creating a new one
2. **Use sections**: When adding to existing packs, specify a section for better organization
3. **Add sources**: When adding content from external docs, use `aio_add_file_to_context_pack` to preserve attribution
4. **Tag appropriately**: Use relevant tags for discoverability
5. **Keep packs focused**: Each pack should cover one domain, system, or process - split if it gets too broad

## Example Workflows

### Capturing Meeting Insights

User: "Add to the Q4 migration context: The team decided to use feature flags for the rollout"

```json
{
  "pack": "q4-migration",
  "content": "### Decision: Feature Flags for Rollout\n\nThe team decided to use feature flags to control the migration rollout, allowing gradual exposure and quick rollback if issues arise.",
  "section": "Decisions"
}
```

### Creating Technical Context

User: "Create a system context for our new notification service"

```json
{
  "title": "Notification Service",
  "category": "system",
  "content": "## Overview\n\nThe notification service handles all user-facing notifications across channels (email, SMS, push).\n\n## Architecture\n\n(To be documented)\n\n## Key Endpoints\n\n(To be documented)",
  "description": "Technical documentation for the notification microservice",
  "tags": ["notifications", "messaging", "alerts"]
}
```

### Recording Process Knowledge

User: "Update the definition of done with: All PRs must have at least 2 approvals"

```json
{
  "pack": "definition-of-done",
  "content": "- [ ] PR has at least 2 approvals",
  "section": "Code Review"
}
```

### Adding an ADR to Context

User: "Add the payment provider ADR to my payments context pack"

```json
{
  "pack": "payments",
  "file": "ADRs/2024-01-payment-provider.md",
  "section": "Architecture Decisions"
}
```
