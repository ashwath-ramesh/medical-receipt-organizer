# Medical Receipt Organizer

Rename medical receipts using local AI. No data leaves your computer.

## Quick Start

1. **Install Ollama** — https://ollama.com/download
2. **Pull vision model** — `ollama pull qwen2.5vl:7b`
3. **Start Ollama** — `ollama serve`
4. **Install & run**:
   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Run directly (uv handles venv automatically)
   uv run receipt-organizer /path/to/receipts --dry-run -v
   ```

## Usage

```bash
# Preview with confirmation prompts (default)
uv run receipt-organizer /path/to/receipts --dry-run -v

# Execute with confirmation prompts (default)
uv run receipt-organizer /path/to/receipts -v

# Skip prompts, use parallel workers
uv run receipt-organizer /path/to/receipts -y -w 8
```

## Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview only, no file changes |
| `-v, --verbose` | Show detailed progress |
| `-y, --yes` | Skip confirmation prompts (enables parallel) |
| `-w, --workers N` | Parallel workers (default: 4, requires `-y`) |
| `--model NAME` | Use different Ollama model |
| `--dpi N` | Image resolution (default: 400) |

## Output Format

Files renamed to: `YYYY-MM-DD_Provider_Patient_Amount.ext`

| Before | After |
|--------|-------|
| `scan001.pdf` | `2024-03-15_DrSmith_JohnDoe_SGD150.pdf` |
| `IMG_2345.jpg` | `2024-06-20_CityHospital_JaneDoe_SGD85.50.jpg` |
| `receipt.png` | `REVIEW_CvsPharmacy_JohnDoe_SGD32.99.png` |

## Supported Formats

PDF, JPG, PNG, BMP, TIFF

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Multi-page PDF | First page only |
| Missing date | `REVIEW` placeholder |
| Missing fields | `UNKNOWN` placeholder |
| Filename conflict | Suffix: `_1`, `_2`, etc. |
| Non-receipt | Skipped automatically |

## Alternative: Traditional venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
receipt-organizer /path/to/receipts --dry-run -v
```
