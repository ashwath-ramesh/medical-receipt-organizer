---
title: "Vision Model Timeout on Large Images"
problem: "Smartphone photos at native resolution (12+ MP) timeout vision model"
solution: "Normalize image DPI to match PDF handling (400 DPI)"
category: "performance-issues"
tags:
  - vision-model
  - timeout
  - dpi
  - image-processing
  - pymupdf
  - parity-bug
component: "processor.py"
date: "2026-01-04"
---

# Vision Model Timeout on Large Images

## Problem

Vision model API calls timed out when processing smartphone photos, but PDFs processed successfully.

## Symptoms

- Timeout errors on large JPEG/PNG files from smartphones
- PDFs of the same content worked fine
- Error messages like "API timeout" or "Request too large"
- Inconsistent behavior depending on file type

## Root Cause

**Inconsistent DPI handling between file types.**

The `_pdf_to_png()` function normalized PDFs to 400 DPI, but `_image_to_png()` processed images at native resolution:

```python
def _pdf_to_png(self, pdf_path: Path) -> bytes:
    with pymupdf.open(str(pdf_path)) as doc:
        page = doc[0]
        pix = page.get_pixmap(dpi=self.dpi)  # ✓ Normalized
        return pix.tobytes("png")

def _image_to_png(self, image_path: Path) -> bytes:
    with pymupdf.open(str(image_path)) as doc:
        page = doc[0]
        pix = page.get_pixmap()  # ✗ Native resolution!
        return pix.tobytes("png")
```

Modern smartphone photos are 12+ megapixels (4000x3000 or larger). When base64-encoded for the vision model API:

| Image Size | Base64 Size | Result |
|------------|-------------|--------|
| 400 DPI normalized | ~200KB | Works |
| 12MP native | ~8MB+ | Timeout |

## Solution

One-line fix: add `dpi=self.dpi` to match PDF handling:

```python
def _image_to_png(self, image_path: Path) -> bytes:
    """Convert image file to PNG bytes, normalized to DPI limit."""
    with pymupdf.open(str(image_path)) as doc:
        page = doc[0]
        pix = page.get_pixmap(dpi=self.dpi)  # ✓ Now normalized
        return pix.tobytes("png")
```

## The Broader Pattern: Function Parity Anti-Pattern

This bug represents a common anti-pattern:

> **When you have similar functions handling variants of the same operation, updates to one often get missed in the other.**

### Detection Signals

- Functions with similar names: `_pdf_to_png()` / `_image_to_png()`
- Parameters that should logically apply to all variants
- One function getting updates without reviewing related functions

### Why It Happens

1. Original implementation normalized PDFs (which can be arbitrarily large)
2. Images "seemed fine" at the time with test files
3. Production data revealed the edge case

### Prevention Strategies

**Option 1: Single Generic Function**
```python
def _to_png(self, file_path: Path) -> bytes:
    """Convert any supported file to normalized PNG bytes."""
    with pymupdf.open(str(file_path)) as doc:
        page = doc[0]
        pix = page.get_pixmap(dpi=self.dpi)  # One place to maintain
        return pix.tobytes("png")
```

**Option 2: Code Review Checklist**
- [ ] Are there related functions that need the same change?
- [ ] Did I update all variants of similar operations?

**Option 3: Test Comparison**
```python
def test_all_formats_produce_similar_size():
    """Ensure consistent processing across file types."""
    processor = FileProcessor(dpi=400)
    pdf_bytes = processor.file_to_image_bytes(Path("test.pdf"))
    jpg_bytes = processor.file_to_image_bytes(Path("test.jpg"))

    # Same content should produce similar sizes
    assert abs(len(pdf_bytes) - len(jpg_bytes)) < 50000
```

## Prevention Checklist

- [ ] When adding parameters to one variant function, check all related functions
- [ ] Use a single generic function when processing is identical
- [ ] Add tests that verify consistent behavior across file types
- [ ] Document why specific parameters (like `dpi`) exist

## Files Modified

| File | Change |
|------|--------|
| `processor.py:70` | Add `dpi=self.dpi` to `_image_to_png()` |

## Result

- 1-line fix
- All file types now processed consistently at 400 DPI
- No more timeouts on smartphone photos
- Base64 payloads stay within API limits
