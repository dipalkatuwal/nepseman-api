"""
tests/test_auth.py
------------------
Unit tests for the auth module.
These tests do NOT require a network connection — they test the local logic only.
Run: python -m pytest tests/ -v
"""

from nepseman_api.auth import PayloadParser, TokenParser


class TestPayloadParser:
    def setup_method(self):
        self.parser = PayloadParser()

    def test_stock_live_returns_base_value(self):
        """stock-live returns base value without salt adjustment."""
        token_details = {
            "salt1": 10, "salt2": 20, "salt3": 30, "salt4": 40, "salt5": 50
        }
        from datetime import datetime
        today = datetime.now().day

        # given_id=0: DUMMY_DATA[0] + 0 + 2*today
        result = self.parser.calculate_payload_id(0, token_details, "stock-live")
        expected = PayloadParser.DUMMY_DATA[0] + 0 + 2 * today
        assert result == expected

    def test_general_payload_applies_salt(self):
        """General payload should be different from stock-live."""
        token_details = {
            "salt1": 10, "salt2": 20, "salt3": 30, "salt4": 40, "salt5": 50
        }
        stock = self.parser.calculate_payload_id(0, token_details, "stock-live")
        general = self.parser.calculate_payload_id(0, token_details, "general")
        assert stock != general

    def test_dummy_data_length(self):
        """dummyData must have exactly 100 entries."""
        assert len(PayloadParser.DUMMY_DATA) == 100

    def test_all_given_ids_in_range(self):
        """All 100 given_id values should compute without IndexError."""
        token_details = {"salt1": 5, "salt2": 3, "salt3": 7, "salt4": 2, "salt5": 9}
        for i in range(100):
            result = self.parser.calculate_payload_id(i, token_details, "general")
            assert isinstance(result, int)


class TestTokenParser:
    def test_wasm_loads(self):
        """WASM binary should load and all 5 exported functions should be callable."""
        parser = TokenParser()
        # Call each WASM function with dummy salt values
        for fn in (parser.cdx, parser.rdx, parser.bdx, parser.ndx, parser.mdx):
            result = fn(parser.store, 10, 20, 30, 40, 50)
            assert isinstance(result, int)
            assert result >= 0
