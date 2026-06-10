"""
auth.py
-------
Handles NEPSE's obfuscated JWT auth scheme.

How NEPSE auth works:
  1. GET /api/authenticate/prove
     → returns { accessToken, refreshToken, salt1..salt5 }

  2. The accessToken/refreshToken are intentionally corrupted — characters
     are inserted at positions computed from the salts. We use NEPSE's own
     WASM binary (nepse.wasm) to compute those positions, then strip the
     injected characters to get the real tokens.

  3. Every subsequent API request sends:
       Authorization: Salter <parsed_accessToken>
     and a JSON body with { "id": <payload_id> }.

  4. The payload_id is derived from:
       - the "id" field returned by /api/nots/nepse-data/market-open
       - today's date
       - the salt values
       - a hardcoded dummyData lookup table (also from the NEPSE JS bundle)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from wasmtime import Instance, Module, Store

logger = logging.getLogger(__name__)

WASM_PATH = Path(__file__).parent / "nepse.wasm"


class TokenParser:
    """
    Loads nepse.wasm and exposes the 5 exported functions (cdx, rdx, bdx, ndx, mdx).

    Each function takes 5 int32 args (the 5 salts in various orders) and returns
    an int32 position used to strip corrupted characters from the JWT strings.
    """

    def __init__(self) -> None:
        self.store: Store = Store()
        module: Module = Module.from_file(self.store.engine, str(WASM_PATH))
        instance: Instance = Instance(self.store, module, [])
        exports = instance.exports(self.store)

        self.cdx: Callable[..., int] = exports["cdx"]
        self.rdx: Callable[..., int] = exports["rdx"]
        self.bdx: Callable[..., int] = exports["bdx"]
        self.ndx: Callable[..., int] = exports["ndx"]
        self.mdx: Callable[..., int] = exports["mdx"]
        logger.debug("TokenParser: WASM module loaded successfully.")

    def parse_token_response(
        self, token_response: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Given the raw /api/authenticate/prove response dict, compute real tokens.

        Args:
            token_response: dict with keys accessToken, refreshToken, salt1..salt5

        Returns:
            (parsed_access_token, parsed_refresh_token)
        """
        s1 = token_response["salt1"]
        s2 = token_response["salt2"]
        s3 = token_response["salt3"]
        s4 = token_response["salt4"]
        s5 = token_response["salt5"]

        n  = self.cdx(self.store, s1, s2, s3, s4, s5)
        m2 = self.rdx(self.store, s1, s2, s4, s3, s5)
        o  = self.bdx(self.store, s1, s2, s4, s3, s5)
        p  = self.ndx(self.store, s1, s2, s4, s3, s5)
        q  = self.mdx(self.store, s1, s2, s4, s3, s5)

        i = self.cdx(self.store, s2, s1, s3, s5, s4)
        r = self.rdx(self.store, s2, s1, s3, s4, s5)
        s = self.bdx(self.store, s2, s1, s4, s3, s5)
        t = self.ndx(self.store, s2, s1, s4, s3, s5)
        u = self.mdx(self.store, s2, s1, s4, s3, s5)

        raw_access  = token_response["accessToken"]
        raw_refresh = token_response["refreshToken"]

        parsed_access = (
            raw_access[0:n] + raw_access[n+1:m2] + raw_access[m2+1:o] +
            raw_access[o+1:p] + raw_access[p+1:q] + raw_access[q+1:]
        )
        parsed_refresh = (
            raw_refresh[0:i] + raw_refresh[i+1:r] + raw_refresh[r+1:s] +
            raw_refresh[s+1:t] + raw_refresh[t+1:u] + raw_refresh[u+1:]
        )

        logger.debug("TokenParser: tokens parsed successfully.")
        return parsed_access, parsed_refresh


class PayloadParser:
    """
    Computes the dynamic `id` value required in POST request bodies.
    """

    DUMMY_DATA = [
        147, 117, 239, 143, 157, 312, 161, 612, 512, 804,
        411, 527, 170, 511, 421, 667, 764, 621, 301, 106,
        133, 793, 411, 511, 312, 423, 344, 346, 653, 758,
        342, 222, 236, 811, 711, 611, 122, 447, 128, 199,
        183, 135, 489, 703, 800, 745, 152, 863, 134, 211,
        142, 564, 375, 793, 212, 153, 138, 153, 648, 611,
        151, 649, 318, 143, 117, 756, 119, 141, 717, 113,
        112, 146, 162, 660, 693, 261, 362, 354, 251, 641,
        157, 178, 631, 192, 734, 445, 192, 883, 187, 122,
        591, 731, 852, 384, 565, 596, 451, 772, 624, 691,
    ]

    def calculate_payload_id(
        self,
        given_id: int,
        token_details: Dict[str, Any],
        which: str,
    ) -> int:
        today = datetime.now().day
        payload_id = self.DUMMY_DATA[given_id] + given_id + 2 * today

        if which == "stock-live":
            return payload_id

        salts = [token_details.get(f"salt{i}", 0) for i in range(1, 6)]

        if which == "sector-live":
            idx = 1 if payload_id % 10 < 4 else 3
        else:
            idx = 3 if payload_id % 10 < 5 else 1

        payload_id = payload_id + salts[idx] * today - salts[idx - 1]
        return payload_id
