# Quick Start Guide

## Installation

```bash
git clone https://github.com/yu-min/xml-base64-decoder.git
cd xml-base64-decoder
```

Requires Python 3.7+ and the `defusedxml` library for secure XML parsing. Install it using `pip install defusedxml`.

## Basic Usage

### 1. Use an Existing XML File

Prepare an existing XML file that contains Base64-encoded content (elements marked with `base64="true"` will be decoded):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<root>
  <item>
    <request base64="true"><![CDATA[UE9TVCAvYXBpIEhUVFAvMS4xDQpIb3N0OiBleGFtcGxlLmNvbQ==]]></request>
  </item>
</root>
```

### 2. Run the Decoder

```bash
python3 xml_decoder.py your_file.xml
```

### 3. Save Output to File

```bash
python3 xml_decoder.py your_file.xml -o output.txt
```

## Common Commands

```bash
# Basic decode (display in console)
python3 xml_decoder.py input.xml

# Decode and save
python3 xml_decoder.py input.xml -o results.txt

# Quiet mode (minimal output)
python3 xml_decoder.py input.xml -q -o results.txt

# Keep original escape sequences
python3 xml_decoder.py input.xml --no-expand-json

# Limit XML and Base64 sizes
python3 xml_decoder.py input.xml --max-xml-size 1000000 --max-b64-size 10000

# Raw output (no escaping of control characters)
python3 xml_decoder.py input.xml --raw-output

# Use built-in (unsafe) XML parser
python3 xml_decoder.py input.xml --unsafe-xml

# Show help
python3 xml_decoder.py -h
```

## Example Output

**Input:**
```xml
<request base64="true">eyJuYW1lIjoiSm9obiIsImFnZSI6MzB9</request>
```

**Output:**
```json
{
  "name": "John",
  "age": 30
}
```

## Testing with Sample File

```bash
cd examples
python3 ../xml_decoder.py sample_input.xml -o sample_output.txt
```

## Troubleshooting

**Problem:** Script doesn't run  
**Solution:** Make sure you have Python 3.10+ installed

```bash
python3 --version  # Should show 3.10 or higher
```

**Problem:** Chinese characters show as `???`  
**Solution:** Set UTF-8 encoding in your terminal

```bash
export LANG=en_US.UTF-8
```

## Next Steps

- Read the full [README.md](README.md) for advanced features
- Check the [examples](examples/) directory for more samples
- Explore command-line options with `-h`

## Support

Questions? Open an issue on GitHub!
