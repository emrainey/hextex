import sys
import argparse
from typing import List, Optional
from . import HexTex, BinFile

width_choices = [1, 2, 4, 8]


def add_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("HEXTEX - Hex Editor in Textual")
    parser.add_argument("input", type=str, help="The file to examine")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        choices=width_choices,
        default=width_choices[0],
        help="Display width",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = add_parser()
    args = parser.parse_args(argv)
    bf = BinFile(args.input)
    bf.load()  # read it all, keep it internally
    app = HexTex(bf, args.width)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
