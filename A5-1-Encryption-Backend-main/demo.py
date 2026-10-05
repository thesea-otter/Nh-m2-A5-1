# -*- coding: utf-8 -*-
"""Command-line encryption demo for the A5 backend."""

import argparse
import json

from service.cipher_service import CipherService


DEFAULT_TINY_KEY = "10010101001110100110000"
DEFAULT_FULL_KEY = "0001000100100010001100110100010001010101011001100111011110001000"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Encryption-only backend demo: A5/1 and Tiny A5/1"
    )
    parser.add_argument(
        "--algorithm",
        choices=["a5/1", "a5/1-tiny"],
        default="a5/1-tiny",
        help="Encryption algorithm (default: a5/1-tiny)",
    )
    parser.add_argument(
        "--plaintext", default="Xin chào A5/1!", help="UTF-8 plaintext"
    )
    parser.add_argument(
        "--key", help="Binary key (64 bits for A5/1, 23 bits for Tiny)"
    )
    parser.add_argument(
        "--frame", type=int, help="22-bit frame for A5/1; Tiny requires 0"
    )
    args = parser.parse_args()

    service = CipherService()
    key = args.key or (
        DEFAULT_TINY_KEY if args.algorithm == "a5/1-tiny" else DEFAULT_FULL_KEY
    )
    frame = args.frame if args.frame is not None else (
        0 if args.algorithm == "a5/1-tiny" else 7
    )

    print("Algorithm info:")
    print(json.dumps(service.info(args.algorithm), ensure_ascii=False, indent=2))

    result = service.encrypt_text(
        args.algorithm,
        plaintext=args.plaintext,
        key_binary=key,
        frame=frame,
    )
    print("\nEncryption result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
