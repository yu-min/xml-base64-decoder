#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XML Base64 Decoder - Enhanced Version
Properly handles UTF-8 Chinese characters, Unicode escape sequences, and string escape characters
"""

import base64
import binascii
import xml.etree.ElementTree as ET
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any


class XMLDecoder:
    """Enhanced XML Base64 Decoder with full escape sequence support"""
    
    def __init__(self, verbose=True, unescape_strings=True, expand_json_strings=True):
        """
        Initialize the decoder
        
        Args:
            verbose: Print detailed information to console
            unescape_strings: Decode escape sequences in HTTP headers
            expand_json_strings: Expand escape sequences in JSON string values
        """
        self.verbose = verbose
        self.unescape_strings = unescape_strings
        self.expand_json_strings = expand_json_strings
        self.decoded_count = 0
    
    @staticmethod
    def decode_escape_sequences(text: str) -> str:
        """
        Decode escape sequences in strings for better readability
        
        Args:
            text: Text containing escape sequences
            
        Returns:
            Text with escape sequences decoded
        """
        escape_map = {
            'n': '\n',
            'r': '\r',
            't': '\t',
            '"': '"',
            "'": "'",
            '\\': '\\',
        }

        result = []
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in escape_map:
                    result.append(escape_map[next_char])
                    i += 2
                    continue
            result.append(text[i])
            i += 1

        return ''.join(result)
    
    def expand_json_escape_sequences(self, obj: Any) -> Any:
        """
        Recursively expand escape sequences in all string values of a JSON object
        
        Args:
            obj: JSON object (dict, list, str, etc.)
            
        Returns:
            Object with expanded escape sequences
        """
        if isinstance(obj, dict):
            return {k: self.expand_json_escape_sequences(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.expand_json_escape_sequences(item) for item in obj]
        elif isinstance(obj, str):
            return self.decode_escape_sequences(obj)
        else:
            return obj
    
    def _try_decode_base64(self, base64_string: str) -> Optional[str]:
        """
        Properly decode base64 without corrupting UTF-8 Chinese characters
        
        Args:
            base64_string: Base64 encoded string
            
        Returns:
            Decoded string
        """
        try:
            base64_string = base64_string.strip()
            decoded_bytes = base64.b64decode(base64_string, validate=True)
            decoded_text = decoded_bytes.decode('utf-8', errors='replace')
            
            # Handle \uxxxx Unicode escape sequences
            def replace_unicode_escape(match):
                try:
                    return chr(int(match.group(1), 16))
                except:
                    return match.group(0)
            
            final_text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode_escape, decoded_text)
            
            return final_text
            
        except (ValueError, binascii.Error) as e:
            if self.verbose:
                print(f"Decoding error: {e}")
            return None

    def decode_base64_correctly(self, base64_string: str) -> str:
        """
        Decode base64 and keep backward-compatible return type.
        Returns original input when decoding fails.
        """
        decoded = self._try_decode_base64(base64_string)
        return decoded if decoded is not None else base64_string
    
    def extract_and_format_json(self, text: str) -> tuple[Optional[Any], Optional[str]]:
        """
        Extract and format JSON data from text
        
        Returns:
            (original JSON object, formatted JSON string)
        """
        try:
            decoder = json.JSONDecoder()
            for match in re.finditer(r'[\{\[]', text):
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
    
    def format_http_request(self, text: str) -> str:
        """
        Format HTTP request for better readability
        
        Args:
            text: HTTP request text
            
        Returns:
            Formatted text
        """
        if not (text.startswith('POST') or text.startswith('GET') or 
                text.startswith('PUT') or text.startswith('DELETE') or
                text.startswith('PATCH') or text.startswith('HEAD')):
            return text
        
        parts = text.split('\n\n', 1)
        if len(parts) != 2:
            parts = text.split('\r\n\r\n', 1)
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
    
    def create_readable_text_view(self, json_obj: dict) -> str:
        """
        Create a plain text readable view of JSON (all escape sequences fully expanded)
        
        Args:
            json_obj: JSON object
            
        Returns:
            Plain text formatted content
        """
        if not json_obj:
            return ""
        
        lines = []
        lines.append("=" * 80)
        lines.append("JSON Content (Plain Text View - All Escape Sequences Expanded)")
        lines.append("=" * 80)
        
        def format_value(value, indent=0):
            prefix = "  " * indent
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        format_value(v, indent + 1)
                    else:
                        if isinstance(v, str):
                            v_expanded = self.decode_escape_sequences(v)
                            if '\n' in v_expanded:
                                lines.append(f"{prefix}{k}:")
                                for line in v_expanded.split('\n'):
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
    
    def process_element(self, element: ET.Element) -> Optional[Dict]:
        """
        Process a single XML element
        
        Args:
            element: XML element
            
        Returns:
            Decoded result dictionary
        """
        if element.get('base64') != 'true':
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
        
        result = {
            'tag': element.tag,
            'original_length': len(content),
            'decoded_length': len(decoded_content),
            'decoded_content': formatted_content,
            'json_data': json_obj,
            'formatted_json': formatted_json,
            'text_view': text_view
        }
        
        if self.verbose:
            self._print_result(result)
        
        return result
    
    def _print_result(self, result: Dict):
        """
        Print decoded result to console
        
        Args:
            result: Decoded result dictionary
        """
        print(f"\n{'='*80}")
        print(f"Tag: <{result['tag']}>")
        print(f"Original Length: {result['original_length']} bytes")
        print(f"Decoded Length: {result['decoded_length']} bytes")
        print(f"{'='*80}")
        print(f"\nDecoded Content:\n")
        print(result['decoded_content'])
        
        if result['formatted_json']:
            print(f"\n{'-'*80}")
            print("JSON Data (Formatted):")
            print(f"{'-'*80}")
            print(result['formatted_json'])
        
        if result['text_view']:
            print(f"\n{result['text_view']}")
    
    def process_file(self, input_file: str, output_file: Optional[str] = None) -> List[Dict]:
        """
        Process XML file
        
        Args:
            input_file: Input XML file path
            output_file: Output file path (optional)
            
        Returns:
            List of decoded results
        """
        results = []
        
        try:
            tree = ET.parse(input_file)
            root = tree.getroot()
            
            if self.verbose:
                print(f"\nProcessing XML file: {input_file}")
                print(f"{'='*80}\n")
            
            for element in root.iter():
                result = self.process_element(element)
                if result:
                    results.append(result)
            
            if output_file and results:
                self._save_results(results, output_file)
            
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
        except FileNotFoundError:
            print(f"File not found: {input_file}")
        except Exception as e:
            print(f"Error processing file: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _save_results(self, results: List[Dict], output_file: str):
        """
        Save decoded results to file
        
        Args:
            results: List of decoded results
            output_file: Output file path
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("XML Base64 Decoding Results (Enhanced Version)\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, result in enumerate(results, 1):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Item {idx}: <{result['tag']}>\n")
                    f.write(f"Original Length: {result['original_length']} bytes\n")
                    f.write(f"Decoded Length: {result['decoded_length']} bytes\n")
                    f.write(f"{'='*80}\n\n")
                    
                    f.write("Decoded Content:\n")
                    f.write("-" * 80 + "\n")
                    f.write(result['decoded_content'])
                    f.write("\n\n")
                    
                    if result['formatted_json']:
                        f.write("JSON Data (Formatted):\n")
                        f.write("-" * 80 + "\n")
                        f.write(result['formatted_json'])
                        f.write("\n\n")
                    
                    if result['text_view']:
                        f.write(result['text_view'])
                        f.write("\n\n")
            
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Results saved to: {output_file}")
                print(f"{'='*80}")
                
        except Exception as e:
            print(f"Error saving file: {e}")


def main():
    """
    Main function with command-line argument support
    """
    parser = argparse.ArgumentParser(
        description='Decode Base64 encoded content in XML files (Enhanced Version)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 xml_decoder.py input.xml
  python3 xml_decoder.py input.xml -o output.txt
  python3 xml_decoder.py input.xml -o output.txt -q
  python3 xml_decoder.py input.xml --no-expand-json
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Input XML file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (optional)',
        default=None
    )
    
    parser.add_argument(
        '-q', '--quiet',
        help='Quiet mode (suppress detailed output)',
        action='store_true'
    )
    
    parser.add_argument(
        '--no-unescape',
        help='Do not decode escape sequences in HTTP headers',
        action='store_true'
    )
    
    parser.add_argument(
        '--no-expand-json',
        help='Do not expand escape sequences in JSON strings',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File does not exist - {args.input_file}")
        return 1
    
    decoder = XMLDecoder(
        verbose=not args.quiet,
        unescape_strings=not args.no_unescape,
        expand_json_strings=not args.no_expand_json
    )
    
    results = decoder.process_file(args.input_file, args.output)
    
    if not args.quiet:
        print(f"\n{'='*80}")
        print(f"Processing complete! Decoded {len(results)} base64-encoded items")
        if not args.no_unescape:
            print(f"HTTP header escape sequences decoded")
        if not args.no_expand_json:
            print(f"JSON string escape sequences expanded")
        print(f"{'='*80}")
    
    return 0


def simple_run():
    """
    Simple run mode - specify file paths directly in code
    """
    input_file = "input.xml"
    output_file = "output.txt"
    
    print("=" * 80)
    print("XML Base64 Decoder - Enhanced Version")
    print("=" * 80)
    
    if not Path(input_file).exists():
        print(f"\nError: Input file does not exist - {input_file}")
        print("Please modify the input_file variable in the code")
        return
    
    decoder = XMLDecoder(
        verbose=True,
        unescape_strings=True,
        expand_json_strings=True
    )
    
    results = decoder.process_file(input_file, output_file)
    
    print(f"\n{'='*80}")
    print(f"Processing complete! Decoded {len(results)} items")
    print(f"All escape sequences fully expanded for readability")
    print(f"{'='*80}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        sys.exit(main())
    else:
        print("\nTip: You can use command-line arguments")
        print("Usage: python3 xml_decoder.py input.xml -o output.txt")
        print("\nRunning in simple mode...\n")
        simple_run()
