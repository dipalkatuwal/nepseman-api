/**
 * auth.ts
 * -------
 * NEPSE token deobfuscation + POST payload ID computation.
 *
 * In the Python package this was backed by nepse.wasm via wasmtime.
 * In Node.js we use the built-in WebAssembly API — same WASM binary,
 * loaded at runtime via fs.readFileSync.
 *
 * Note: The WASM binary itself is served by nepalstock.com. We bundle
 * a copy in this package for convenience, but you can also pass the
 * binary as a Buffer if you want to fetch it fresh.
 */

import fs from "fs";
import path from "path";

// Hardcoded lookup table extracted from NEPSE JS bundle
const DUMMY_DATA = [
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
];

export interface RawTokenResponse {
  accessToken: string;
  refreshToken: string;
  salt1: number;
  salt2: number;
  salt3: number;
  salt4: number;
  salt5: number;
}

type WasmExports = {
  cdx: (s1: number, s2: number, s3: number, s4: number, s5: number) => number;
  rdx: (s1: number, s2: number, s3: number, s4: number, s5: number) => number;
  bdx: (s1: number, s2: number, s3: number, s4: number, s5: number) => number;
  ndx: (s1: number, s2: number, s3: number, s4: number, s5: number) => number;
  mdx: (s1: number, s2: number, s3: number, s4: number, s5: number) => number;
};

export class TokenParser {
  private exports!: WasmExports;

  /**
   * Load and compile the WASM module.
   * @param wasmBinary - path to nepse.wasm, or raw Buffer. Defaults to bundled copy.
   */
  async init(wasmBinary?: string | Buffer): Promise<void> {
    let buf: Buffer;
    if (wasmBinary instanceof Buffer) {
      buf = wasmBinary;
    } else {
      const wasmPath = wasmBinary ?? path.join(__dirname, "nepse.wasm");
      buf = fs.readFileSync(wasmPath);
    }
    const module = await WebAssembly.compile(new Uint8Array(buf));
    const instance = await WebAssembly.instantiate(module, {});
    this.exports = instance.exports as unknown as WasmExports;
  }

  /** Parse corrupted tokens from /api/authenticate/prove response. */
  parseTokens(raw: RawTokenResponse): { accessToken: string; refreshToken: string } {
    const { salt1: s1, salt2: s2, salt3: s3, salt4: s4, salt5: s5 } = raw;
    const { cdx, rdx, bdx, ndx, mdx } = this.exports;

    // Access token slice positions
    const n  = cdx(s1, s2, s3, s4, s5);
    const m2 = rdx(s1, s2, s4, s3, s5);
    const o  = bdx(s1, s2, s4, s3, s5);
    const p  = ndx(s1, s2, s4, s3, s5);
    const q  = mdx(s1, s2, s4, s3, s5);

    // Refresh token slice positions (salts swapped)
    const i = cdx(s2, s1, s3, s5, s4);
    const r = rdx(s2, s1, s3, s4, s5);
    const s = bdx(s2, s1, s4, s3, s5);
    const t = ndx(s2, s1, s4, s3, s5);
    const u = mdx(s2, s1, s4, s3, s5);

    const ra = raw.accessToken;
    const rr = raw.refreshToken;

    const accessToken =
      ra.slice(0, n) + ra.slice(n + 1, m2) + ra.slice(m2 + 1, o) +
      ra.slice(o + 1, p) + ra.slice(p + 1, q) + ra.slice(q + 1);

    const refreshToken =
      rr.slice(0, i) + rr.slice(i + 1, r) + rr.slice(r + 1, s) +
      rr.slice(s + 1, t) + rr.slice(t + 1, u) + rr.slice(u + 1);

    return { accessToken, refreshToken };
  }
}

export type PayloadType = "stock-live" | "sector-live" | "general";

export function calculatePayloadId(
  givenId: number,
  tokenDetails: RawTokenResponse,
  which: PayloadType
): number {
  const today = new Date().getDate();
  let payloadId = DUMMY_DATA[givenId] + givenId + 2 * today;

  if (which === "stock-live") return payloadId;

  const salts = [
    tokenDetails.salt1,
    tokenDetails.salt2,
    tokenDetails.salt3,
    tokenDetails.salt4,
    tokenDetails.salt5,
  ];

  const idx = which === "sector-live"
    ? (payloadId % 10 < 4 ? 1 : 3)
    : (payloadId % 10 < 5 ? 3 : 1);

  payloadId = payloadId + salts[idx] * today - salts[idx - 1];
  return payloadId;
}
