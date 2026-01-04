---
title: Python version specified doesn't exist yet
date: 2026-01-04
category: build-errors
tags: [python, pyproject, ci, ruff, github-actions]
severity: high
components: [pyproject.toml, .github/workflows/ci.yml]
---

## Problem

CI fails immediately with Python version not found, or ruff fails with "unknown variant" error.

**Error examples:**

```
# GitHub Actions
Error: Python version 3.14 not found

# Ruff
TOML parse error at line 29, column 18
   |
29 | target-version = "py314"
   |                  ^^^^^^^
unknown variant `py314`, expected one of `py37`, `py38`, `py39`, `py310`, `py311`, `py312`, `py313`
```

## Root Cause

Using a Python version that hasn't been officially released yet. Even if you have a pre-release version installed locally (e.g., Python 3.14.0a1), it won't work in:

1. **GitHub Actions** - Only stable Python versions are available
2. **Ruff** - Only supports released Python versions as target-version
3. **Package installation** - Other users can't install your package

## Solution

Use the latest **stable** Python version:

```toml
# pyproject.toml
requires-python = ">=3.10"  # Broad compatibility

[tool.ruff]
target-version = "py313"    # Latest stable that ruff supports
```

```yaml
# .github/workflows/ci.yml
- name: Set up Python
  run: uv python install 3.13  # Latest stable
```

## Prevention

1. **Check Python release status** before specifying versions: https://www.python.org/downloads/
2. **Use minimum required version** for `requires-python` (broader compatibility)
3. **Use latest stable** for CI and ruff target-version
4. **Don't assume local Python version is stable** - check with `python --version`

## Related

- Python release schedule: https://peps.python.org/pep-0719/
- Ruff supported versions: Check ruff changelog for newly added versions
