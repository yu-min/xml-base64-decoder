# XML Base64 Decoder

A powerful Python tool for decoding Base64-encoded content in XML files, with special support for UTF-8 Chinese characters, Unicode escape sequences, and string escape characters.

## Features

✅ **Base64 Decoding**: Automatically detects and decodes `base64="true"` XML elements  
✅ **UTF-8 Support**: Properly handles Chinese and other multi-byte characters  
✅ **Unicode Escapes**: Converts `\uxxxx` sequences to actual characters  
✅ **Escape Sequences**: Expands `\n`, `\t`, `\"`, etc. for better readability  
✅ **JSON Formatting**: Auto-detects and pretty-prints JSON content  
✅ **HTTP Request Formatting**: Formats HTTP requests with proper line breaks  
✅ **Plain Text View**: Creates readable plain-text representation of JSON data  
✅ **Command-Line Interface**: Easy to use with flexible options  

## Installation

### Requirements

- Python 3.10 or higher
- No external dependencies required (uses only Python standard library)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yu-min/xml-base64-decoder.git
cd xml-base64-decoder

# Make the script executable (optional)
chmod +x xml_decoder.py

# Run the decoder
python xml_decoder.py input.xml
```

## Usage

### Basic Usage

```bash
# Decode and display results in console
python xml_decoder.py input.xml

# Decode and save to file
python xml_decoder.py input.xml -o output.txt

# Quiet mode (only show summary)
python xml_decoder.py input.xml -o output.txt -q
```

### Advanced Options

```bash
# Keep escape sequences in HTTP headers (don't expand \n, \t, etc.)
python xml_decoder.py input.xml --no-unescape

# Keep escape sequences in JSON strings
python xml_decoder.py input.xml --no-expand-json

# Both options together
python xml_decoder.py input.xml --no-unescape --no-expand-json -o output.txt
```

### Help

```bash
python xml_decoder.py -h
```

## Input Format

The tool processes XML files containing Base64-encoded content. Elements with `base64="true"` attribute will be decoded:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <item>
    <request base64="true"><![CDATA[UE9TVCAvYXBpL3YzL3YxL2NoYXQvY29tcGxldGlvbnM...]]></request>
    <response base64="true"><![CDATA[SGVsbG8gV29ybGQ=]]></response>
  </item>
</root>
```

## Output Features

### 1. HTTP Request Formatting

**Before:**
```
POST /api HTTP/1.1\nHost: example.com\nContent-Type: application/json\n\n{"key":"value"}
```

**After:**
```
POST /api HTTP/1.1
Host: example.com
Content-Type: application/json

{
  "key": "value"
}
```

### 2. JSON Pretty-Printing

Automatically detects and formats JSON content with proper indentation.

### 3. Escape Sequence Expansion

**Before:**
```json
{
  "content": "Line 1\nLine 2\nLine 3"
}
```

**After (Plain Text View):**
```
content:
  Line 1
  Line 2
  Line 3
```

### 4. Unicode Character Decoding

Converts `\u6587` → `文`, `\u4ef6` → `件`, etc.

## Examples

### Example 1: Basic HTTP Request

**Input XML:**
```xml
<request base64="true">UE9TVCAvYXBpIEhUVFAvMS4xDQpIb3N0OiBleGFtcGxlLmNvbQ0KDQp7ImhlbGxvIjoid29ybGQifQ==</request>
```

**Output:**
```
POST /api HTTP/1.1
Host: example.com

{
  "hello": "world"
}
```

### Example 2: Traditional Chinese Content

**Input XML:**
```xml
<data base64="true">eyJuYW1lIjoi546L5bCP5piOIiwiY2l0eSI6IuWPsOWMlyJ9</data>
```

**Output:**
```json
{
  "name": "王小明",
  "city": "台北"
}
```

### Example 3: Complex JSON with Escape Sequences

See the `examples/` directory for more complex examples.

## Project Structure

```
xml-base64-decoder/
├── xml_decoder.py          # Main decoder script
├── README.md               # This file
├── LICENSE                 # MIT License
├── examples/               # Example input files
│   ├── sample_input.xml
└── tests/                  # Test files (optional)
    └── test_decoder.py
```

## API Usage

You can also use the decoder as a Python module:

```python
from xml_decoder import XMLDecoder

# Create decoder instance
decoder = XMLDecoder(
    verbose=True,
    unescape_strings=True,
    expand_json_strings=True
)

# Process file
results = decoder.process_file('input.xml', 'output.txt')

# Access results
for result in results:
    print(f"Tag: {result['tag']}")
    print(f"Content: {result['decoded_content']}")
    if result['json_data']:
        print(f"JSON: {result['json_data']}")
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `input_file` | Input XML file path (required) |
| `-o, --output` | Output file path (optional) |
| `-q, --quiet` | Quiet mode - suppress detailed output |
| `--no-unescape` | Don't decode escape sequences in HTTP headers |
| `--no-expand-json` | Don't expand escape sequences in JSON strings |
| `-h, --help` | Show help message |

## Common Use Cases

### 1. API Traffic Analysis
Decode captured HTTP requests/responses from network traffic logs.

### 2. Log File Processing
Extract and format Base64-encoded content from application logs.

### 3. Data Migration
Convert legacy Base64-encoded XML data to readable format.

### 4. Debugging
Inspect encoded API payloads during development and testing.

## Troubleshooting

### Issue: Chinese characters appear as gibberish

**Solution**: This tool correctly handles UTF-8 encoding. If you still see issues, ensure your terminal supports UTF-8:

```bash
export LANG=en_US.UTF-8
```

### Issue: JSON not formatting properly

**Solution**: The JSON must be valid. Use `--no-expand-json` to see the raw JSON and debug syntax errors.

### Issue: Escape sequences not expanding

**Solution**: Make sure you're not using `--no-unescape` or `--no-expand-json` flags.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**YM** - [GitHub](https://github.com/yu-min)

## Acknowledgments

- Inspired by the need to decode complex XML traffic logs
- Built for cybersecurity professionals and developers
- Special thanks to the open-source community

## Changelog

### Version 1.0.0 (2026-03-03)
- Initial release
- Base64 decoding with UTF-8 support
- Unicode escape sequence handling
- HTTP request formatting
- JSON pretty-printing
- Plain text view generation
- Command-line interface

## Roadmap

- [ ] Add support for gzip-compressed content
- [ ] XML validation before processing
- [ ] Batch file processing
- [ ] Web interface
- [ ] Docker support
- [ ] Additional output formats (CSV, HTML)

## Support

If you encounter any issues or have questions:

- Open an issue on [GitHub](https://github.com/yu-min/xml-base64-decoder/issues)
- Check existing issues for solutions
