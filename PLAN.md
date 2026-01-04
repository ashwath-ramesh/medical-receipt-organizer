# Medical Receipt Organizer - Quality Improvement Plan

## Problem Statement

Current extraction quality is poor. Once files are renamed, they won't change again - **accuracy is paramount, speed is not**.

---

## Root Causes Identified

| Issue | Current State | Impact |
|-------|---------------|--------|
| Model | `granite3.2-vision` (~70% accuracy) | High hallucination, poor DocVQA scores |
| DPI | 200 DPI | Blurry text, OCR failures |
| Extraction | Single-pass, single prompt | No validation or error catching |
| Confidence | None | Can't identify uncertain extractions |
| Review | None | No human oversight for edge cases |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY-FIRST PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. IMAGE PREPROCESSING                                         │
│     ├── 400 DPI rendering (up from 200)                        │
│     ├── Quality detection (blur, contrast)                      │
│     └── Enhancement if needed (denoise, sharpen)               │
│                                                                 │
│  2. EXTRACTION (Qwen2.5-VL 7B)                                 │
│     ├── Few-shot examples in prompt                            │
│     ├── Field-by-field extraction                              │
│     └── Structured JSON output                                  │
│                                                                 │
│  3. SELF-VERIFICATION                                          │
│     ├── Ask model to locate source text for each field         │
│     ├── Generate confidence score per field                    │
│     └── Flag discrepancies                                     │
│                                                                 │
│  4. VALIDATION                                                  │
│     ├── Date format validation (not future)                    │
│     ├── Amount validation (positive number)                    │
│     └── Currency validation (known codes)                      │
│                                                                 │
│  5. ROUTING                                                     │
│     ├── High confidence (>0.9): Auto-process                   │
│     ├── Medium (0.7-0.9): Flag for optional review             │
│     └── Low (<0.7): REQUIRE human confirmation                 │
│                                                                 │
│  6. INTERACTIVE REVIEW (when needed)                           │
│     ├── Show original image + extracted data                   │
│     ├── Allow field-by-field correction                        │
│     └── Confirm before rename                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Better Model (Highest Impact)

**Change**: Replace `granite3.2-vision` with `qwen2.5vl:7b`

| Metric | granite3.2-vision | qwen2.5vl:7b |
|--------|-------------------|--------------|
| DocVQA Accuracy | ~70% | 95.7% |
| Hallucination Rate | High | Low |
| JSON Extraction | Poor | 90%+ |
| Memory (32GB Mac) | ~2GB | ~8GB |

**Files to modify**:
- `receipt_organizer/extractor.py` - Change default model
- `README.md` - Update model pull instructions

**Commands**:
```bash
ollama pull qwen2.5vl:7b
```

---

### Phase 2: Higher Resolution Images

**Change**: Increase DPI from 200 to 400

**Files to modify**:
- `receipt_organizer/processor.py` - Change `dpi=200` to `dpi=400`

---

### Phase 3: Few-Shot Prompting

**Change**: Add concrete examples to the extraction prompt

**New prompt structure**:
```
Here are examples of medical receipt extractions:

EXAMPLE 1:
[Receipt shows: "Dr. Smith Clinic, 15 Mar 2024, Patient: John Doe, Total: S$150.00"]
Output: {"date": "2024-03-15", "provider": "Dr Smith Clinic", "patient": "John Doe", "amount": 150.0, "currency": "SGD", "is_medical_receipt": true}

EXAMPLE 2:
[Receipt shows: "City Hospital, 2024/01/20, Name: Jane Tan, Amount Due: $85.50"]
Output: {"date": "2024-01-20", "provider": "City Hospital", "patient": "Jane Tan", "amount": 85.5, "currency": "SGD", "is_medical_receipt": true}

EXAMPLE 3:
[Electric bill from SP Services]
Output: {"is_medical_receipt": false}

Now analyze this receipt and extract the same fields...
```

**Files to modify**:
- `receipt_organizer/extractor.py` - Update `EXTRACTION_PROMPT`

---

### Phase 4: Self-Verification Pass

**Change**: After extraction, ask the model to verify each field

**New method in `ReceiptExtractor`**:
```python
def verify(self, image_bytes: bytes, extracted: ReceiptData) -> VerificationResult:
    """Ask model to verify extraction against source image."""
    prompt = f"""
    I extracted these fields from the receipt:
    - Date: {extracted.date}
    - Provider: {extracted.provider}
    - Patient: {extracted.patient}
    - Amount: {extracted.amount} {extracted.currency}

    For each field, locate the EXACT text in the image that supports this value.
    Rate your confidence (0.0-1.0) for each field.
    If you cannot find supporting text, set confidence to 0.

    Return JSON: {{"date": {{"value": "...", "source_text": "...", "confidence": 0.95}}, ...}}
    """
```

**Files to modify**:
- `receipt_organizer/extractor.py` - Add `verify()` method
- `receipt_organizer/models.py` - Add `VerificationResult` dataclass

---

### Phase 5: Confidence-Based Routing

**Change**: Add `--confirm` flag for interactive review of low-confidence extractions

**New CLI flow**:
```
receipt-organizer /path --dry-run -v --confirm

[1/23] scan001.pdf
       -> 2024-03-15_DrSmith_JohnDoe_SGD150.pdf
       Confidence: 0.95 ✓ (auto-approved)

[2/23] blurry_receipt.jpg
       -> REVIEW_UNKNOWN_JaneDoe_SGD85.pdf
       Confidence: 0.65 ⚠

       Extracted:
         Date: UNKNOWN (confidence: 0.3)
         Provider: UNKNOWN (confidence: 0.4)
         Patient: Jane Doe (confidence: 0.9)
         Amount: 85.00 SGD (confidence: 0.8)

       [a]ccept / [e]dit / [s]kip? _
```

**Files to modify**:
- `receipt_organizer/cli.py` - Add `--confirm` flag and interactive prompts
- `receipt_organizer/models.py` - Add confidence fields to `ReceiptData`

---

### Phase 6: Image Quality Detection (Deferred)

**Change**: Warn about low-quality images before processing

**Quality checks**:
- Blur detection (Laplacian variance)
- Low contrast warning
- Very dark/bright image warning

**Files to modify**:
- `receipt_organizer/processor.py` - Add `check_quality()` method

---

## Files to Modify

| File | Changes |
|------|---------|
| `receipt_organizer/extractor.py` | New model default, few-shot prompt, verify() method |
| `receipt_organizer/processor.py` | DPI 400 |
| `receipt_organizer/models.py` | Confidence fields, VerificationResult |
| `receipt_organizer/cli.py` | --confirm flag, interactive review |
| `README.md` | Update model instructions |

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Field Accuracy | ~70% | 90-95% |
| Hallucination Rate | High | Low |
| Human Review Needed | 0% (but errors) | ~10-20% (caught) |
| Confidence in Results | Low | High |

---

## User Decisions

| Question | Decision |
|----------|----------|
| Review mode | **Confidence-based** - Auto-approve >0.9, prompt for uncertain |
| Model | **qwen2.5vl:7b** - Best accuracy (95.7%) |
| Verification | **Yes** - Double processing time acceptable for quality |

---

## Final Implementation Scope

✅ Phase 1: Switch to qwen2.5vl:7b
✅ Phase 2: Increase DPI to 400
✅ Phase 3: Add few-shot examples
✅ Phase 4: Add self-verification pass
✅ Phase 5: Add confidence-based interactive review (`--confirm` flag)
⏸️ Phase 6: Image quality detection (defer to later)
