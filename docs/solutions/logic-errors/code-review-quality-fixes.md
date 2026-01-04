---
title: "Code Review Quality Fixes"
problem: "Silent exception swallowing, path traversal risk, unbounded loops, dead code"
solution: "Proper exception handling, path validation, bounded iterations, cleanup"
category: "logic-errors"
tags:
  - error-handling
  - security
  - code-cleanup
  - robustness
component: "receipt_organizer"
date: "2025-01-04"
---

# Code Review Quality Fixes

## Problem

During code review, multiple quality issues were identified:

1. **Silent exception swallowing** - API errors masked as "not a receipt"
2. **Path traversal risk** - No validation in `execute_rename()`
3. **Unbounded loop** - `while True` in conflict resolution
4. **Dead code** - Unused `FileOperation` class and `dry_run` param
5. **Resource leaks** - Manual PyMuPDF cleanup instead of context managers

## Symptoms

- API failures appeared as "Skipped (not a medical receipt)"
- No way to distinguish network errors from actual non-receipts
- Potential infinite loop if 1000+ filename conflicts existed
- 12 lines of unused code

## Root Cause

Over-defensive error handling that masked real problems instead of surfacing them.

## Solution

### 1. Stop Masking Exceptions (P1)

**Before** (`extractor.py`):
```python
try:
    response = self.client.chat(...)
    return ReceiptData.from_json(response.message.content)
except ResponseError:
    return ReceiptData(is_medical_receipt=False)  # Masks real error!
```

**After**:
```python
response = self.client.chat(...)
return ReceiptData.from_json(response.message.content)
# Let exception propagate - caller handles it
```

**Caller** (`cli.py`):
```python
try:
    data = extractor.extract(image_bytes)
except Exception as e:
    result.error = f"extraction failed: {e}"
    print(f"         -> Skipped (extraction failed: {e})")
    return result
```

### 2. Path Validation (P2)

**After** (`renamer.py`):
```python
def execute_rename(self, source: Path, new_name: str) -> Path:
    new_path = source.parent / new_name

    # Prevent path traversal
    if new_path.resolve().parent != source.parent.resolve():
        raise ValueError(f"Path traversal detected: {new_name}")

    source.rename(new_path)
    return new_path
```

### 3. Bounded Loop (P2)

**Before**:
```python
counter = 1
while True:  # Unbounded!
    new_name = f"{stem}_{counter}{ext}"
    if not (directory / new_name).exists():
        return new_name
    counter += 1
```

**After**:
```python
MAX_CONFLICT_ATTEMPTS = 1000

for counter in range(1, self.MAX_CONFLICT_ATTEMPTS + 1):
    new_name = f"{stem}_{counter}{ext}"
    if not (directory / new_name).exists():
        return new_name
raise RuntimeError(f"Could not resolve conflict after {MAX_CONFLICT_ATTEMPTS} attempts")
```

### 4. Context Managers (P3)

**Before**:
```python
doc = pymupdf.open(str(pdf_path))
try:
    page = doc[0]
    pix = page.get_pixmap(dpi=self.dpi)
    return pix.tobytes("png")
finally:
    doc.close()
```

**After**:
```python
with pymupdf.open(str(pdf_path)) as doc:
    page = doc[0]
    pix = page.get_pixmap(dpi=self.dpi)
    return pix.tobytes("png")
```

### 5. Delete Dead Code (P3)

Removed:
- `FileOperation` dataclass (never used)
- `dry_run` parameter in `execute_rename()` (handled by caller)
- `ResponseError` import (no longer caught)

## Prevention Checklist

- [ ] Never catch exceptions just to return a default value
- [ ] Always validate file paths stay within expected directory
- [ ] Add `MAX_ATTEMPTS` to any `while True` loop
- [ ] Use `with` statements for resources (files, connections, locks)
- [ ] Delete unused code immediately - don't leave "for later"
- [ ] Run code review agents before merging

## Files Modified

| File | Changes |
|------|---------|
| `extractor.py` | Remove exception masking |
| `cli.py` | Add proper exception handling |
| `renamer.py` | Add path validation, bounded loop |
| `processor.py` | Use context managers |
| `models.py` | Delete unused FileOperation |

## Result

- Net: -12 lines of code
- Errors now surface with actual messages
- Path traversal attacks blocked
- Infinite loops prevented
- Resources properly cleaned up
