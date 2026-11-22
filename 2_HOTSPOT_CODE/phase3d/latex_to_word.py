"""Convert a LaTeX source file to a Microsoft Word document using Pandoc."""

import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="LaTeX source file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output .docx path (defaults to the input path with a .docx extension)",
    )
    parser.add_argument(
        "--reference-doc",
        type=Path,
        help="optional .docx file whose styles Pandoc should use",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output file if it already exists",
    )
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.is_file():
        parser.error(f"LaTeX input file does not exist: {source}")

    output = (args.output or source.with_suffix(".docx")).resolve()
    if output == source:
        parser.error("The output path must differ from the input path.")
    if not output.parent.is_dir():
        parser.error(f"Output directory does not exist: {output.parent}")
    if output.exists() and not args.force:
        parser.error(f"Output already exists (use --force to overwrite): {output}")

    reference_doc = args.reference_doc.resolve() if args.reference_doc else None
    if reference_doc is not None and not reference_doc.is_file():
        parser.error(f"Reference document does not exist: {reference_doc}")

    pandoc = shutil.which("pandoc")
    if pandoc is None:
        parser.error(
            "Pandoc was not found on PATH. Install Pandoc and make sure the "
            "pandoc command is available."
        )

    command = [
        pandoc,
        "--from=latex",
        "--to=docx",
        str(source),
        f"--output={output}",
    ]
    if reference_doc is not None:
        command.append(f"--reference-doc={reference_doc}")

    result = subprocess.run(command, check=False)
    if result.returncode:
        return result.returncode
    if not output.is_file():
        parser.error(f"Pandoc completed without creating the output file: {output}")

    print(f"Created {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
