"""
Main entry point for sdf_csv_converter.

Orchestrates format detection and dispatches to the correct converter module.
"""
import logging
import sys
from typing import Dict

from . import cli
from . import sdf_to_csv
from . import csv_to_sdf
from . import cdx_to_sdf
from . import cdx_to_csv

logger = logging.getLogger(__name__)


def main() -> None:
    """Main CLI entry point."""
    parser = cli.build_parser()
    args = parser.parse_args()

    # Setup logging
    cli.setup_logging(args)

    # Resolve formats
    input_fmt, output_fmt = cli.resolve_formats(args)

    logger.info(f"Converting: {input_fmt.upper()} → {output_fmt.upper()}")
    logger.info(f"Input:  {args.input}")
    logger.info(f"Output: {args.output}")

    # Dispatch to appropriate converter
    try:
        if input_fmt in ("cdx", "cdxml") and output_fmt == "sdf":
            stats = cdx_to_sdf.convert_cdx_to_sdf(
                input_path=args.input,
                output_path=args.output,
                workers=args.workers,
                generate_3d=args.generate_3d,
                use_v3000=args.v3000,
                no_properties=args.no_properties,
                max_structures=args.max_scan,
            )

        elif input_fmt in ("cdx", "cdxml") and output_fmt == "csv":
            stats = cdx_to_csv.convert_cdx_to_csv(
                input_path=args.input,
                output_path=args.output,
                workers=args.workers,
                no_properties=args.no_properties,
                max_structures=args.max_scan,
            )

        elif input_fmt == "sdf" and output_fmt == "csv":
            stats = sdf_to_csv.convert_sdf_to_csv(
                input_path=args.input,
                output_path=args.output,
                workers=args.workers,
                max_scan=args.max_scan,
                no_properties=args.no_properties,
                chunk_size=args.chunk_size,
            )

        elif input_fmt == "csv" and output_fmt == "sdf":
            stats = csv_to_sdf.convert_csv_to_sdf(
                input_path=args.input,
                output_path=args.output,
                smiles_col=args.smiles_col,
                workers=args.workers,
                generate_3d=args.generate_3d,
                use_v3000=args.v3000,
                max_scan=args.max_scan,
                chunk_size=args.chunk_size,
            )

        else:
            logger.error(f"Unsupported conversion: {input_fmt} → {output_fmt}")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Conversion failed: {e}")
        sys.exit(1)

    # Print summary
    _print_summary(stats, input_fmt, output_fmt, args.output)


def _print_summary(
    stats: Dict[str, int],
    input_fmt: str,
    output_fmt: str,
    output_path: str,
) -> None:
    """Print conversion summary to stderr."""
    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Conversion complete: {input_fmt.upper()} → {output_fmt.upper()}", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    print(f"  Total:    {stats.get('total', 0):>8}", file=sys.stderr)
    print(f"  Success:  {stats.get('success', 0):>8}", file=sys.stderr)
    print(f"  Failed:   {stats.get('failed', 0):>8}", file=sys.stderr)
    if stats.get("skipped", 0) > 0:
        print(f"  Skipped:  {stats.get('skipped', 0):>8}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()