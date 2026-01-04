"""CLI entry point using argparse."""
import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import ReceiptData
from .extractor import ReceiptExtractor
from .processor import FileProcessor
from .renamer import FileRenamer


@dataclass
class ProcessResult:
    """Result of processing a single file."""
    file_path: Path
    data: Optional[ReceiptData] = None
    new_name: Optional[str] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


# Lock for thread-safe printing and conflict resolution
print_lock = threading.Lock()


def process_single_file(
    file_path: Path,
    processor: FileProcessor,
    extractor: ReceiptExtractor,
    renamer: FileRenamer,
    dry_run: bool,
    verbose: bool,
    confirm: bool,
    counter: dict,
    total: int
) -> ProcessResult:
    """Process a single file (thread-safe).

    Args:
        file_path: Path to the file
        processor: FileProcessor instance
        extractor: ReceiptExtractor instance
        renamer: FileRenamer instance
        dry_run: Whether this is a dry run
        verbose: Whether to show verbose output
        counter: Shared counter dict for progress
        total: Total number of files

    Returns:
        ProcessResult with extracted data or error
    """
    result = ProcessResult(file_path=file_path)

    # Convert to image
    image_bytes = processor.file_to_image_bytes(file_path)
    if image_bytes is None:
        result.error = "failed to read file"
        with print_lock:
            counter['done'] += 1
            print(f"[{counter['done']}/{total}] {file_path.name}")
            print(f"         -> Skipped (failed to read)")
        return result

    # Extract data via LLM
    data = extractor.extract(image_bytes)
    result.data = data

    # Check if it's a medical receipt
    if not data.is_medical_receipt:
        result.skipped_reason = "not a medical receipt"
        with print_lock:
            counter['done'] += 1
            print(f"[{counter['done']}/{total}] {file_path.name}")
            print(f"         -> Skipped (not a medical receipt)")
        return result

    # Generate new filename (thread-safe with lock)
    with print_lock:
        new_name = renamer.generate_new_name(data, file_path.suffix)
        new_name = renamer.resolve_conflict(file_path.parent, new_name)
        result.new_name = new_name

        counter['done'] += 1
        print(f"[{counter['done']}/{total}] {file_path.name}")
        print(f"         -> {new_name}")
        if verbose:
            print(f"            Date: {data.date or 'UNKNOWN'}")
            print(f"            Provider: {data.provider or 'UNKNOWN'}")
            print(f"            Patient: {data.patient or 'UNKNOWN'}")
            print(f"            Amount: {data.amount or 'UNKNOWN'} {data.currency}")

        # Confirm and execute rename
        if confirm:
            action = "Rename" if not dry_run else "Mark for rename"
            response = input(f"         {action}? [Y/n] ").strip().lower()
            if response == 'n':
                print("         Skipped by user")
                result.skipped_reason = "skipped by user"
                result.new_name = None  # Don't count as processed
                return result

        if not dry_run:
            renamer.execute_rename(file_path, new_name)

    return result


def process_files(
    directory: Path,
    model: str,
    dry_run: bool,
    verbose: bool,
    workers: int,
    dpi: int = 400,
    confirm: bool = False
) -> tuple[int, int, int]:
    """Process all files in directory.

    Returns:
        Tuple of (processed_count, skipped_count, failed_count)
    """
    # Initialize components
    extractor = ReceiptExtractor(model=model)
    processor = FileProcessor(dpi=dpi)
    renamer = FileRenamer()

    # Check Ollama is available
    available, error = extractor.check_available()
    if not available:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    # Discover files
    files = processor.discover_files(directory)
    if not files:
        print("No supported files found.")
        return 0, 0, 0

    total = len(files)

    # Force single worker for confirm mode (sequential prompts)
    if confirm:
        workers = 1

    print(f"Found {total} file(s) to process using {workers} worker(s)")
    if dry_run:
        print("DRY RUN - no files will be renamed")
    print()

    # Shared counter for progress
    counter = {'done': 0}

    # Process files in parallel
    results: list[ProcessResult] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                process_single_file,
                f, processor, extractor, renamer,
                dry_run, verbose, confirm, counter, total
            )
            for f in files
        ]

        for future in as_completed(futures):
            results.append(future.result())

    # Count results
    processed = sum(1 for r in results if r.new_name)
    skipped = sum(1 for r in results if r.skipped_reason)
    failed = sum(1 for r in results if r.error)

    return processed, skipped, failed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="receipt-organizer",
        description="Organize medical receipts using AI-powered extraction. "
                    "Uses local Ollama - no data leaves your computer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/receipts --dry-run -v    Preview renames
  %(prog)s /path/to/receipts -v              Execute renames
  %(prog)s /path/to/receipts --workers 8     Use 8 parallel workers
        """
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Directory to scan for receipts (scans recursively)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview renames without executing"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed extraction for each file"
    )

    parser.add_argument(
        "--model",
        default="qwen2.5vl:7b",
        help="Ollama vision model to use (default: qwen2.5vl:7b)"
    )

    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=400,
        help="Image resolution for processing (default: 400)"
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompts (auto-approve all)"
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"ERROR: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"ERROR: Not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Validate workers
    if args.workers < 1:
        print("ERROR: Workers must be at least 1", file=sys.stderr)
        sys.exit(1)

    # Print run info
    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"Model: {args.model} | DPI: {args.dpi} | Mode: {mode}")
    print()

    # Process files
    processed, skipped, failed = process_files(
        directory=args.directory,
        model=args.model,
        dry_run=args.dry_run,
        verbose=args.verbose,
        workers=args.workers,
        dpi=args.dpi,
        confirm=not args.yes
    )

    # Print summary
    print()
    print("=" * 40)
    action = "Would rename" if args.dry_run else "Renamed"
    print(f"{action}: {processed} file(s)")
    print(f"Skipped (not receipts): {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
