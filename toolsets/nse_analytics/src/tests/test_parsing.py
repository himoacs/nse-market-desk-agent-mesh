import json
import unittest

from _helpers import fixture_raw, fixture_text

from nse_analytics.parsing import extract_payload


class ExtractPayloadTest(unittest.TestCase):
    def setUp(self):
        self.text = fixture_text("breadth_2026-09-30.json")
        self.expected = json.loads(self.text)

    def test_bare_payload_text(self):
        self.assertEqual(extract_payload(self.text), self.expected)

    def test_bytes(self):
        self.assertEqual(extract_payload(self.text.encode()), self.expected)

    def test_call_tool_result(self):
        wrapped = json.dumps({"content": [{"type": "text", "text": self.text}], "isError": False})
        self.assertEqual(extract_payload(wrapped), self.expected)

    def test_jsonrpc_envelope(self):
        self.assertEqual(extract_payload(fixture_raw("breadth_2026-09-30.json")), self.expected)

    def test_content_item_list(self):
        self.assertEqual(extract_payload([{"type": "text", "text": self.text}]), self.expected)

    def test_sse_framing(self):
        envelope = fixture_raw("breadth_2026-09-30.json").replace("\n", "")
        sse = f"event: message\nid: 1\ndata: {envelope}\n\n"
        self.assertEqual(extract_payload(sse), self.expected)

    def test_prose_preamble(self):
        self.assertEqual(extract_payload("Tool result:\n" + self.text + "\n"), self.expected)

    def test_structured_content(self):
        wrapped = {"content": [], "structuredContent": self.expected}
        self.assertEqual(extract_payload(wrapped), self.expected)

    def test_is_error_raises(self):
        with self.assertRaises(ValueError):
            extract_payload({"content": [{"type": "text", "text": "boom"}], "isError": True})

    def test_nse_error_object_raises(self):
        # cm_get_live_market_data answers an invalid index with HTTP 200 and this body.
        with self.assertRaises(ValueError):
            extract_payload('{"error":"Invalid index \'NIFTY BANK\'. Valid values: gainers, loosers"}')

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            extract_payload("no json here")


if __name__ == "__main__":
    unittest.main()
