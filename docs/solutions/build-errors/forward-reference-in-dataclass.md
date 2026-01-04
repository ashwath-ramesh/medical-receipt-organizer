---
title: Forward reference undefined name error after ruff auto-fix
date: 2026-01-04
category: build-errors
tags: [python, ruff, dataclass, type-hints, forward-reference]
severity: medium
components: [models.py]
---

## Problem

Ruff's `UP037` rule removes quotes from type annotations, but this breaks forward references in the same class:

```python
@dataclass
class ReceiptData:
    @classmethod
    def from_json(cls, json_str: str) -> ReceiptData:  # F821 Undefined name
        ...
```

**Error:**
```
F821 Undefined name `ReceiptData`
```

## Root Cause

When a classmethod returns an instance of its own class, the class name isn't defined yet at parse time. Ruff's `UP037` rule (Remove quotes from type annotation) removes the protective quotes from `"ReceiptData"`, exposing the forward reference issue.

## Solution

Add `from __future__ import annotations` at the top of the file:

```python
"""Data models for receipt extraction."""

from __future__ import annotations  # Add this

import json
from dataclasses import dataclass

@dataclass
class ReceiptData:
    @classmethod
    def from_json(cls, json_str: str) -> ReceiptData:  # Now works
        ...
```

This enables PEP 563 postponed evaluation of annotations, treating all annotations as strings at runtime.

## Alternative Solutions

1. **Keep quotes** (disable UP037 for this line):
   ```python
   def from_json(cls, json_str: str) -> "ReceiptData":  # noqa: UP037
   ```

2. **Use `Self` type** (Python 3.11+):
   ```python
   from typing import Self

   def from_json(cls, json_str: str) -> Self:
   ```

## Prevention

When creating dataclasses or classes with self-referential type hints:
1. Always add `from __future__ import annotations` at file top
2. This is safe and forward-compatible (will be default in future Python)
