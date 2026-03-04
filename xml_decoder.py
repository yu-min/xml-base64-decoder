#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure XML Base64 Decoder

This module provides an enhanced and hardened implementation of the XML
Base64 decoder originally found in the `xml-base64-decoder` project.
It mitigates common XML parsing and Base64 decoding vulnerabilities by
leveraging the defusedxml library, enforcing optional size limits on input
files and payloads, validating Base64 alphabets, and sanitising console
output to prevent terminal escape injection.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try to import the secure XML parser.  If unavailable, fall back to the
# standard library; insecure parsing can be explicitly enabled via CLI.
try:
    from defusedxml import ElementTree as SafeET  # type: ignore[assignment]
except Exception:
    SafeET = None  # type: ignore[assignment]

import xml.etree.ElementTree as ET


class XMLDecoder:
    """
    Enhanced XML Base64 Decoder with robust security controls.

    Parameters
    ----------
    verbose : bool, optional
        Whether to print detailed information to the console. Default is True.
    unescape_strings : bool, optional
        Whether to decode escape sequences in HTTP header strings. Default is True.
    expand_json_strings : bool, optional
        Whether to expand escape sequences in JSON string values. Default is True.
    max_xml_size : Optional[int], optional
        Maximum allowable XML file size in bytes. If None, no limit is enforced.
    max_base64_size : Optional[int], optional
        Maximum allowable Base64 payload length (in characters). If None, no limit.
    use_secure_parser : bool, optional
        If True and defusedxml is available, parse XML with the secure parser.
    escape_output : bool, optional
        If True, sanitise control characters (e.g., ANSI escapes) before printing.
    """

    def __init__(
        self,
        *,
        verbose: bool = True,
        unescape_strings: bool = True,
        expand_json_strings: bool = True,
        max_xml_size: Optional[int] = None,
        max_base64_size: Optional[int] = None,
        use_secure_parser: bool = True,
        escape_output: bool = True,
    ) -> None:
        self.verbose = verbose
        self.unescape_strings = unescape_strings
        self.expand_json_strings = expand_json_strings
        self.max_xml_size = max_xml_size
        self.max_base64_size = max_base64_size
        self.use_secure_parser = use_secure_parser
        self.escape_output = escape_output
        self.decoded_count: int = 0

    # ----------------------------------------------------------------------
    # Escape sequence utilities
    # ----------------------------------------------------------------------
    @staticmethod
    def decode_escape_sequences(text: str) -> str:
        """
        Decode common escape sequences (\n, \r, \t, \" etc.) in a string.
        Unknown escape sequences are left intact.
        """
        escape_map = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            '"': '"',
            "'": "'",
            "\\": "\\",
        }
        result: List[str] = []
        i = 0
        while i < len(text):
            if text[i] == "\\" and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in escape_map:
                    result.append(escape_map[next_char])
                    i += 2
                    continue
            result.append(text[i])
            i += 1
        return "".join(result)

    def expand_json_escape_sequences(self, obj: Any) -> Any:
        """
        Recursively expand escape sequences in all string values of a JSON object.
        """
        if isinstance(obj, dict):
            return {k: self.expand_json_escape_sequences(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.expand_json_escape_sequences(item) for item in obj]
        if isinstance(obj, str):
            return self.decode_escape_sequences(obj)
        return obj

    # ----------------------------------------------------------------------
    # Base64 validation and decoding
    # ----------------------------------------------------------------------
    _BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")

    def _is_valid_base64(self, s: str) -> bool:
        """
        Check whether the provided string conforms to the standard Base64 alphabet.
        """
        return bool(self._BASE64_PATTERN.fullmatch(s))

    def _try_decode_base64(self, base64_string: str) -> Optional[str]:
        """
        Decode a Base64 string with optional length and alphabet validation.

        Returns the decoded text on success or None on failure.
        """
        base64_string = base64_string.strip()
        # Enforce maximum payload size if specified
        if self.max_base64_size is not None and len(base64_string) > self.max_base64_size:
            if self.verbose:
                print(
                    f"Skipping payload: Base64 string length {len(base64_string)} exceeds "
                    f"configured limit ({self.max_base64_size} characters)"
                )
            return None
        # Validate Base64 characters to mitigate CVE-2025-12781 (unexpected alphabet)
        if not self._is_valid_base64(base64_string):
            if self.verbose:
                print("Skipping payload: invalid Base64 characters detected")
            return None

        try:
            decoded_bytes = base64.b64decode(base64_string, validate=True)
        except (ValueError, binascii.Error) as e:
            if self.verbose:
                print(f"Decoding error: {e}")
            return None

        # Decode to text; unknown bytes replaced to avoid exceptions
        decoded_text = decoded_bytes.decode("utf-8", errors="replace")

        # Convert explicit \uXXXX sequences into their Unicode equivalents
        def replace_unicode_escape(match: re.Match[str]) -> str:
            try:
                return chr(int(match.group(1), 16))
            except Exception:
                return match.group(0)

        final_text = re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode_escape, decoded_text)
        return final_text

    # ----------------------------------------------------------------------
    # JSON extraction and formatting
    # ----------------------------------------------------------------------
    def extract_and_format_json(self, text: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Extract the first JSON object or array found in the input text and pretty-print it.

        Returns a tuple (json_obj, formatted_json) where json_obj is the original
        parsed object and formatted_json is a pretty-printed JSON string. If no
        valid JSON is found, both values are None.
        """
        try:
            decoder = json.JSONDecoder()
            for match in re.finditer(r"[\{\[]", text):
                start = match.start()
                try:
                    json_obj, _ = decoder.raw_decode(text[start:])
                except json.JSONDecodeError:
                    continue
                if self.expand_json_strings:
                    expanded_obj = self.expand_json_escape_sequences(json_obj)
                    formatted = json.dumps(expanded_obj, ensure_ascii=False, indent=2)
                else:
                    formatted = json.dumps(json_obj, ensure_ascii=False, indent=2)
                return json_obj, formatted
        except Exception as e:
            if self.verbose:
                print(f"JSON extraction/formatting failed: {e}")
        return None, None

    # ----------------------------------------------------------------------
    # HTTP request formatting
    # ----------------------------------------------------------------------
    def format_http_request(self, text: str) -> str:
        """
        If the input text appears to be an HTTP request, pretty‑print the
        headers and JSON body (if present). Otherwise, return the input unmodified.
        """
        if not text:
            return text
        # Check for common HTTP verbs
        if not text.startswith(("POST", "GET", "PUT", "DELETE", "PATCH", "HEAD")):
            return text
        # Split headers and body on first blank line (CRLF or LF)
        parts = text.split("\n\n", 1)
        if len(parts) != 2:
            parts = text.split("\r\n\r\n", 1)
            if len(parts) != 2:
                return text
        headers, body = parts
        if self.unescape_strings:
            headers = self.decode_escape_sequences(headers)
        if body.strip():
            json_obj, formatted_json = self.extract_and_format_json(body)
            if formatted_json:
                return f"{headers}\n\n{formatted_json}"
        return f"{headers}\n\n{body}"

    # ----------------------------------------------------------------------
    # JSON plain text view
    # ----------------------------------------------------------------------
    def create_readable_text_view(self, json_obj: Dict[str, Any]) -> str:
        """
        Generate a plain text view of a JSON object, expanding escape sequences
        in string values for readability.
        """
        if not json_obj:
            return ""
        lines: List[str] = []
        lines.append("=" * 80)
        lines.append("JSON Content (Plain Text View - All Escape Sequences Expanded)")
        lines.append("=" * 80)

        def format_value(value: Any, indent: int = 0) -> None:
            prefix = "  " * indent
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        format_value(v, indent + 1)
                    else:
                        if isinstance(v, str):
                            v_expanded = self.decode_escape_sequences(v)
                            if "\n" in v_expanded:
                                lines.append(f"{prefix}{k}:")
                                for line in v_expanded.split("\n"):
                                    lines.append(f"{prefix}  {line}")
                            else:
                                lines.append(f"{prefix}{k}: {v_expanded}")
                        else:
                            lines.append(f"{prefix}{k}: {v}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    lines.append(f"{prefix}[{i}]:")
                    format_value(item, indent + 1)
            else:
                lines.append(f"{prefix}{value}")

        format_value(json_obj)
        return "\n".join(lines)

    # ----------------------------------------------------------------------
    # XML parsing and processing
    # ----------------------------------------------------------------------
    def _get_parser(self) -> Any:
        """
        Return the appropriate XML parser module based on configuration.
        """
        if self.use_secure_parser and SafeET is not None:
            return SafeET
        return ET

    def process_element(self, element: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Process a single XML element.  Only elements with attribute base64="true"
        are decoded and returned.  Non‑conforming or invalid payloads are ignored.
        """
        if element.get("base64") != "true":
            return None
        content = element.text
        if not content or not content.strip():
            return None
        decoded_content = self._try_decode_base64(content)
        if decoded_content is None:
            return None
        self.decoded_count += 1
        formatted_content = self.format_http_request(decoded_content)
        json_obj, formatted_json = self.extract_and_format_json(formatted_content)
        text_view = None
        if json_obj and self.expand_json_strings:
            text_view = self.create_readable_text_view(json_obj)
        result: Dict[str, Any] = {
            "tag": element.tag,
            "original_length": len(content),
            "decoded_length": len(decoded_content),
            "decoded_content": formatted_content,
            "json_data": json_obj,
            "formatted_json": formatted_json,
            "text_view": text_view,
        }
        if self.verbose:
            self._print_result(result)
        return result

    def _print_result(self, result: Dict[str, Any]) -> None:
        """
        Print a single decoded result to the console.  Control characters are
        sanitised when configured.
        """
        def sanitise(text: str) -> str:
            if not self.escape_output or not text:
                return text
            # Replace ASCII control chars (< 0x20) and the ESC (0x1b) with hex escapes
            return "".join(
                c
                if (" " <= c <= "~" and c != "\x1b")
                else f"\\x{ord(c):02x}"
                for c in text
            )

        print(f"\n{'=' * 80}")
        print(f"Tag: <{result['tag']}>")
        print(f"Original Length: {result['original_length']} bytes")
        print(f"Decoded Length: {result['decoded_length']} bytes")
        print(f"{'=' * 80}\n")
        print("Decoded Content:\n")
        print(sanitise(result["decoded_content"]))
        if result["formatted_json"]:
            print(f"\n{'-' * 80}")
            print("JSON Data (Formatted):")
            print(f"{'-' * 80}")
            print(result["formatted_json"])
        if result["text_view"]:
            print(f"\n{result['text_view']}")

    def process_file(self, input_file: str, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse and process all elements from an XML file.  Returns a list of decoded
        result dictionaries for each Base64 element encountered.  Results can be
        optionally saved to an output file.
        """
        results: List[Dict[str, Any]] = []
        # Enforce maximum file size if specified
        if self.max_xml_size is not None:
            try:
                size = Path(input_file).stat().st_size
                if size > self.max_xml_size:
                    print(
                        f"Skipping file: size {size} bytes exceeds limit "
                        f"({self.max_xml_size} bytes)"
                    )
                    return results
            except FileNotFoundError:
                print(f"File not found: {input_file}")
                return results

        parser_module = self._get_parser()
        try:
            tree = parser_module.parse(input_file)  # type: ignore[call-arg]
            root = tree.getroot()
            if self.verbose:
                print(f"\nProcessing XML file: {input_file}")
                print(f"{'=' * 80}\n")
            for element in root.iter():
                res = self.process_element(element)
                if res:
                    results.append(res)
            if output_file and results:
                self._save_results(results, output_file)
        except Exception as e:
            # Catch parsing or unexpected errors.  defusedxml raises specific
            # exceptions for DTD or entity expansion attempts.
            print(f"XML parsing error: {e}")
        return results

    def _save_results(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Save a list of decoded results to a text file.  Output is similar to the
        console presentation.
        """
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("XML Base64 Decoding Results (Secure Version)\n")
                f.write("=" * 80 + "\n\n")
                for idx, result in enumerate(results, 1):
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"Item {idx}: <{result['tag']}>\n")
                    f.write(f"Original Length: {result['original_length']} bytes\n")
                    f.write(f"Decoded Length: {result['decoded_length']} bytes\n")
                    f.write(f"{'=' * 80}\n\n")
                    f.write("Decoded Content:\n")
                    f.write("-" * 80 + "\n")
                    f.write(result["decoded_content"])
                    f.write("\n\n")
                    if result["formatted_json"]:
                        f.write("JSON Data (Formatted):\n")
                        f.write("-" * 80 + "\n")
                        f.write(result["formatted_json"])
                        f.write("\n\n")
                    if result["text_view"]:
                        f.write(result["text_view"])
                        f.write("\n\n")
            if self.verbose:
                print(f"\n{'=' * 80}")
                print(f"Results saved to: {output_file}")
                print(f"{'=' * 80}")
        except Exception as e:
            print(f"Error saving file: {e}")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Command‑line interface for the secure XML Base64 decoder.
    """
    parser = argparse.ArgumentParser(
        description="Decode Base64 encoded content in XML files (Secure Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 xml_decoder.py input.xml\n"
            "  python3 xml_decoder.py input.xml -o output.txt\n"
            "  python3 xml_decoder.py input.xml -o output.txt -q\n"
            "  python3 xml_decoder.py input.xml --no-expand-json\n"
        ),
    )
    parser.add_argument("input_file", help="Input XML file path")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (optional)",
        default=None,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="Quiet mode (suppress detailed output)",
        action="store_true",
    )
    parser.add_argument(
        "--no-unescape",
        help="Do not decode escape sequences in HTTP headers",
        action="store_true",
    )
    parser.add_argument(
        "--no-expand-json",
        help="Do not expand escape sequences in JSON strings",
        action="store_true",
    )
    parser.add_argument(
        "--raw-output",
        help="Do not sanitise control characters in console output",
        action="store_true",
    )
    parser.add_argument(
        "--max-xml-size",
        type=int,
        default=None,
        help="Maximum XML file size in bytes (default: unlimited)",
    )
    parser.add_argument(
        "--max-b64-size",
        type=int,
        default=None,
        help="Maximum Base64 payload length (characters) (default: unlimited)",
    )
    parser.add_argument(
        "--unsafe-xml",
        action="store_true",
        help="Use the standard XML parser (disables protections against XXE and entity expansion)",
    )
    args = parser.parse_args(argv)
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File does not exist - {args.input_file}")
        return 1
    decoder = XMLDecoder(
        verbose=not args.quiet,
        unescape_strings=not args.no_unescape,
        expand_json_strings=not args.no_expand_json,
        max_xml_size=args.max_xml_size,
        max_base64_size=args.max_b64_size,
        use_secure_parser=not args.unsafe_xml,
        escape_output=not args.raw_output,
    )
    results = decoder.process_file(args.input_file, args.output)
    if not args.quiet:
        print(f"\n{'=' * 80}")
        print(f"Processing complete! Decoded {len(results)} base64-encoded items")
        if not args.no_unescape:
            print("HTTP header escape sequences decoded")
        if not args.no_expand_json:
            print("JSON string escape sequences expanded")
        if args.max_xml_size is not None:
            print(f"Max XML size enforced: {args.max_xml_size} bytes")
        if args.max_b64_size is not None:
            print(f"Max Base64 size enforced: {args.max_b64_size} characters")
        print(f"{'=' * 80}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)