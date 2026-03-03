import unittest
import xml.etree.ElementTree as ET
import base64
import tempfile
from pathlib import Path

from xml_decoder import XMLDecoder


class XMLDecoderTests(unittest.TestCase):
    def setUp(self):
        self.decoder = XMLDecoder(verbose=False)

    def test_invalid_base64_is_not_counted(self):
        element = ET.fromstring('<request base64="true">not-base64***</request>')
        result = self.decoder.process_element(element)

        self.assertIsNone(result)
        self.assertEqual(self.decoder.decoded_count, 0)

    def test_extract_json_picks_first_valid_object(self):
        text = 'prefix {"a":1} middle {"b":2}'
        json_obj, formatted = self.decoder.extract_and_format_json(text)

        self.assertEqual(json_obj, {"a": 1})
        self.assertIn('"a": 1', formatted)

    def test_escape_sequence_expansion_preserves_escaped_backslash(self):
        self.assertEqual(self.decoder.decode_escape_sequences(r'\n'), '\n')
        self.assertEqual(self.decoder.decode_escape_sequences(r'\\n'), r'\n')

    def test_extract_json_supports_array_payload(self):
        text = 'prefix ["a", {"k": 1}] suffix'
        json_obj, formatted = self.decoder.extract_and_format_json(text)

        self.assertEqual(json_obj, ["a", {"k": 1}])
        self.assertIn('"k": 1', formatted)

    def test_format_http_request_pretty_prints_json_body(self):
        request = (
            'POST /api/users HTTP/1.1\r\n'
            'Host: example.com\r\n'
            'Content-Type: application/json\r\n\r\n'
            '{"name":"Alice","age":30}'
        )

        formatted = self.decoder.format_http_request(request)
        self.assertIn('POST /api/users HTTP/1.1', formatted)
        self.assertIn('"name": "Alice"', formatted)
        self.assertIn('"age": 30', formatted)

    def test_process_file_counts_only_valid_base64_elements(self):
        valid_payload = base64.b64encode(b'{"ok":true}').decode('ascii')
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<root>\n'
            f'  <request base64="true">{valid_payload}</request>\n'
            '  <response base64="true">not-base64***</response>\n'
            '  <data base64="false">SGVsbG8=</data>\n'
            '</root>\n'
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = Path(tmpdir) / 'input.xml'
            xml_path.write_text(xml_content, encoding='utf-8')

            results = self.decoder.process_file(str(xml_path))

        self.assertEqual(len(results), 1)
        self.assertEqual(self.decoder.decoded_count, 1)
        self.assertEqual(results[0]['tag'], 'request')


if __name__ == '__main__':
    unittest.main()
