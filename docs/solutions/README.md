# Compound Learnings

A searchable knowledge base of solved problems. Each documented solution compounds your team's knowledge—the first time you solve a problem takes research; the next occurrence takes minutes.

## How It Works

```
First time solving a problem  → 30 min research
Document the solution         → 5 min
Next occurrence              → 2 min lookup
```

## Adding a New Solution

1. Copy `_template.md` to the appropriate category directory
2. Rename with a descriptive slug: `n-plus-one-query-in-extraction.md`
3. Fill in the YAML frontmatter and sections
4. Commit with message: `docs: add solution for [brief description]`

## Categories

| Directory | Use For |
|-----------|---------|
| `build-errors/` | Compilation, dependency, packaging issues |
| `test-failures/` | Test flakiness, assertion failures, fixture problems |
| `runtime-errors/` | Exceptions, crashes, unhandled errors |
| `performance-issues/` | Slow queries, memory leaks, CPU spikes |
| `database-issues/` | Migrations, schema, data integrity |
| `security-issues/` | Vulnerabilities, auth problems, data exposure |
| `ui-bugs/` | Display issues, layout problems, rendering |
| `integration-issues/` | API failures, external service problems |
| `logic-errors/` | Incorrect behavior, edge cases, business logic |

## YAML Frontmatter Schema

```yaml
---
title: Brief, descriptive title
date: YYYY-MM-DD
category: one of the categories above
tags: [ollama, extraction, json-parsing]
severity: low | medium | high | critical
components: [extractor.py, models.py]
---
```

## Searching Solutions

Use grep to find relevant solutions:

```bash
# Find solutions by tag
grep -r "tags:.*ollama" docs/solutions/

# Find solutions by component
grep -r "components:.*extractor" docs/solutions/

# Full-text search
grep -ri "json parsing" docs/solutions/
```

## Best Practices

- **Document while fresh**: Capture solutions immediately after solving
- **Include error messages**: Exact error text helps future searches
- **Show the fix**: Include before/after code snippets
- **Explain why**: Root cause matters more than the fix itself
- **Add prevention**: How to avoid this problem in the future
