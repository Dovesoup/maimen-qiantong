import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import mcp_client
import collect_menus


class FakeResponse:
    def __init__(self, body):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def rpc_text(text, is_error=False):
    return json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"isError": is_error, "content": [{"type": "text", "text": text}]},
    })


class McpClientTests(unittest.TestCase):
    def test_parses_plain_json_and_trailing_text(self):
        self.assertEqual(mcp_client.extract_json('{"data": {"items": []}}'),
                         {"data": {"items": []}})

    def test_parses_actual_json_after_documentation_marker(self):
        text = "Fields: `{\"example\": true}`\n## Original Response\n" \
               '{"data":{"stores":[{"storeCode":"123"}]}}\nEnd of response.'
        self.assertEqual(mcp_client.extract_json(text),
                         {"data": {"stores": [{"storeCode": "123"}]}})

    def test_call_returns_current_plain_json_tool_content(self):
        payload = {"data": [{"storeCode": "123"}]}
        with mock.patch.dict(os.environ, {"MCD_MCP_TOKEN": "test-token"}), \
                mock.patch.object(mcp_client.urllib.request, "urlopen",
                                  return_value=FakeResponse(rpc_text(json.dumps(payload)))):
            self.assertEqual(mcp_client.call("query-nearby-stores", {}), payload)

    def test_call_returns_current_mixed_tool_content(self):
        payload = {"data": {"meals": {}}}
        text = "Response fields follow.\n## Original Response\n" + json.dumps(payload)
        with mock.patch.dict(os.environ, {"MCD_MCP_TOKEN": "test-token"}), \
                mock.patch.object(mcp_client.urllib.request, "urlopen",
                                  return_value=FakeResponse(rpc_text(text))):
            self.assertEqual(mcp_client.call("query-meals", {}), payload)

    def test_rejects_json_rpc_errors(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1,
                           "error": {"code": -32602, "message": "invalid params"}})
        with self.assertRaises(mcp_client.McpError):
            mcp_client._parse_response(body)

    def test_rejects_tool_errors(self):
        with self.assertRaises(mcp_client.McpError):
            mcp_client._parse_response(rpc_text('{"data":{}}', is_error=True))

    def test_rejects_explicit_business_errors(self):
        with self.assertRaises(mcp_client.McpError):
            mcp_client._parse_response(rpc_text('{"success":false,"message":"failed"}'))

    def test_rejects_business_code_message_without_data(self):
        with self.assertRaises(mcp_client.McpError):
            mcp_client._parse_response(rpc_text('{"code":600058,"message":"missing query"}'))

    def test_does_not_reuse_old_raw_tool_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = pathlib.Path(temp_dir)
            old_response = cache / "raw_query-meals.txt"
            old_response.write_text('{"data":{"meals":{"stale":{}}}}')
            with mock.patch.object(mcp_client, "CACHE", cache), \
                    mock.patch.dict(os.environ, {"MCD_MCP_TOKEN": "test-token"}), \
                    mock.patch.object(mcp_client.urllib.request, "urlopen",
                                      return_value=FakeResponse("not JSON")):
                with self.assertRaises(mcp_client.McpError):
                    mcp_client.call("query-meals", {})
            self.assertEqual(old_response.read_text(), '{"data":{"meals":{"stale":{}}}}')

    def test_token_is_required_only_when_calling(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(mcp_client.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(mcp_client.McpError):
                mcp_client.call("query-meals", {})
            urlopen.assert_not_called()

    def test_extracts_bigmac_prices(self):
        payload = {"data": {"meals": {
            "one": {"name": "巨无霸", "currentPrice": "29"},
            "two": {"name": "套餐", "currentPrice": "40"},
        }}}
        self.assertEqual(mcp_client.bigmac_price(payload)[0]["currentPrice"], "29")
        self.assertEqual(len(mcp_client.bigmac_price(payload)), 1)

    def test_incomplete_menu_run_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = pathlib.Path(temp_dir) / "menus.json"
            snapshot_path.write_text('{"previous":"complete"}')
            snapshot = {"北京市": {"slots": {
                "morning": [{"name": "早餐"}],
                "main": [{"name": "正餐"}],
            }}}
            complete, _samples = collect_menus._save_complete_snapshot(
                snapshot_path, snapshot, failures=["上海市"], expected_cities=2)
            self.assertFalse(complete)
            self.assertEqual(snapshot_path.read_text(), '{"previous":"complete"}')

    def test_complete_menu_run_replaces_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = pathlib.Path(temp_dir) / "menus.json"
            snapshot_path.write_text('{"previous":"complete"}')
            snapshot = {"北京市": {"slots": {
                "morning": [{"name": "早餐"}],
                "main": [{"name": "正餐"}],
            }}}
            complete, _samples = collect_menus._save_complete_snapshot(
                snapshot_path, snapshot, failures=[], expected_cities=1)
            self.assertTrue(complete)
            self.assertEqual(json.loads(snapshot_path.read_text()), snapshot)


if __name__ == "__main__":
    unittest.main()
