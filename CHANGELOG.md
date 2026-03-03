# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Support for gzip-compressed content
- XML validation before processing
- Batch file processing (multiple input files)
- Web interface
- Docker support
- Additional output formats (CSV, HTML)

## [1.0.0] - 2026-03-03

### Added
- Initial release of XML Base64 Decoder
- Base64 decoding with full UTF-8 support for Chinese and other multi-byte characters
- Unicode escape sequence handling (`\uxxxx` → actual characters)
- String escape sequence expansion (`\n`, `\t`, `\"`, etc.)
- HTTP request formatting (auto-detects POST/GET/PUT/DELETE/PATCH/HEAD)
- JSON auto-detection and pretty-printing
- Plain text view generation for JSON content
- Command-line interface with flexible options:
  - `-o / --output` for saving results to file
  - `-q / --quiet` for minimal console output
  - `--no-unescape` to preserve HTTP header escape sequences
  - `--no-expand-json` to preserve JSON string escape sequences
- Python module API for programmatic use
- Sample input XML file in `examples/` directory
- Comprehensive documentation (README, QUICKSTART)

[1.0.0]: https://github.com/yu-min/xml-base64-decoder/releases/tag/v1.0.0
