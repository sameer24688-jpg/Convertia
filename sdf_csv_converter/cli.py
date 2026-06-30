"""
Command-line interface for sdf_csv_converter.

Usage:
    sdf_csv_converter.exe <input> -o <output> [options]

Auto-detects input/output formats from file extensions.
Use --from and --to to override.
"""
import argparse
import logging
import sys
from typing import Optional

from . import __version__

logger = logging.getLogger(__name__)

# Supported input formats
INPUT_FORMATS = {"sdf", "csv", "cdx", "cdxml"}
# Supported output formats
OUTPUT_FORMATS = {"sdf", "csv"}


def detect_format(filepath: str) -> Optional[str]:
    """Detect format from file extension."""
    if not filepath or filepath == "-":
        return None
    ext = filepath.lower().rsplit(".", 1)[-1] if "." in filepath else ""
    if ext in INPUT_FORMATS or ext in OUTPUT_FORMATS:
        return ext
    return None


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sdf_csv_converter",
        description=(
            "Universal cheminformatics format converter.\n"
            "Input: SDF, CSV, CDX, CDXML\n"
            "Output: SDF, CSV\n\n"
            "Examples:\n"
            "  sdf_csv_converter.exe library.sdf -o library.csv\n"
            "  sdf_csv_converter.exe compounds.csv -o compounds.sdf --smiles-col Structure\n"
            "  sdf_csv_converter.exe Table-1.cdxml -o Table-1.sdf\n"
            "  sdf_csv_converter.exe Table-1.cdxml -o Table-1.csv\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        help="Input file path (.sdf, .csv, .cdx, .cdxml)",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output file path (.sdf or .csv)",
    )
    parser.add_argument(
        "--from",
        dest="from_format",
        choices=["sdf", "csv", "cdx", "cdxml"],
        help="Force input format (overrides auto-detection)",
    )
    parser.add_argument(
        "--to",
        dest="to_format",
        choices=["sdf", "csv"],
        help="Force output format (overrides auto-detection)",
    )
    parser.add_argument(
        "--smiles-col",
        default="SMILES",
        help='CSV column name containing SMILES strings (default: "SMILES")',
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of parallel workers (default: CPU count - 1)",
    )
    parser.add_argument(
        "--3d",
        dest="generate_3d",
        action="store_true",
        help="Generate 3D coordinates (ETKDG + MMFF optimization)",
    )
    parser.add_argument(
        "--v3000",
        action="store_true",
        help="Write SDF in V3000 format (default: V2000)",
    )
    parser.add_argument(
        "--no-properties",
        action="store_true",
        help="Skip RDKit property computation (faster, SMILES only)",
    )
    parser.add_argument(
        "--max-scan",
        type=int,
        default=0,
        help="Max molecules/structures to process (0 = all)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Molecules per parallel chunk (default: 100)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any input error instead of skipping (for CSV→SDF multiline validation)",
    )
    parser.add_argument(
        "--log-file",
        help="Write errors/warnings to a log file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sdf_csv_converter v{__version__}",
    )

    return parser


def resolve_formats(
    args: argparse.Namespace,
) -> tuple:
    """
    Resolve input and output formats from args or auto-detection.

    Returns:
        (input_format, output_format)
    """
    # Input format
    input_fmt = args.from_format
    if not input_fmt:
        input_fmt = detect_format(args.input)
    if not input_fmt:
        print(
            f"Error: Cannot detect input format from '{args.input}'. "
            f"Use --from to specify.",
            file=sys.stderr,
        )
        sys.exit(1)
    if input_fmt not in INPUT_FORMATS:
        print(
            f"Error: Unsupported input format '{input_fmt}'. "
            f"Supported: {', '.join(sorted(INPUT_FORMATS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Output format
    output_fmt = args.to_format
    if not output_fmt:
        output_fmt = detect_format(args.output)
    if not output_fmt:
        print(
            f"Error: Cannot detect output format from '{args.output}'. "
            f"Use --to to specify.",
            file=sys.stderr,
        )
        sys.exit(1)
    if output_fmt not in OUTPUT_FORMATS:
        print(
            f"Error: Unsupported output format '{output_fmt}'. "
            f"Supported: {', '.join(sorted(OUTPUT_FORMATS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    return input_fmt, output_fmt


def setup_logging(args: argparse.Namespace) -> None:
    """Configure logging based on args."""
    level = logging.DEBUG if args.verbose else logging.INFO

    handlers = []
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))
    handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )