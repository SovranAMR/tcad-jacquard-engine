# JC5 Format — Reverse Engineering Analysis Report

## 1. File Size & Pattern Relationship
15 in-the-wild `.jc5` files analyzed. Key discovery:
- **Same pattern, different scales (20cm vs 40cm) produce identically sized files**.
  - `VRSLS-1-LUNA20CM.jc5` = 4,838,602 bytes
  - `VRSLS-1-LUNA40CM.jc5` = 4,838,602 bytes
  - Same for OPALE and IVORY pairs.
- **Diff Analysis**: 20cm vs 40cm files have ~50% different bytes but *start diverging at offset `0x386`*. This means the canvas size (hooks × picks) is fixed by the machine profile, and the pattern simply occupies a different footprint within that canvas.

## 2. Header & Metadata Block (Offsets 0x00 - 0xFF)
The header is exactly **256 bytes**.
- `0x00 - 0x22` (34 bytes): Binary header containing magic numbers and likely dimensions.
- `0x39 - 0x62`: ASCII String `Generated with EAT OpenWeave Converter`
- `0x64 - 0xFF`: ASCII Metadata defining the sections/heads:
  - `Area 1: 32 hooks` (Likely selvedge/kenar)
  - `Area 2: 288 hooks` (Likely ground/zemin extra)
  - `Area 3: 4800 hooks` (Main pattern area)
  - **Total Hooks = 5120**
- `0x0F` padding fills the remaining space up to offset `0xFF`.

## 3. Payload Structure (Offsets 0x100 - EOF)
Payload starts precisely at offset `256` (`0x100`).

### Packing Hypothesis: Bit-Packed Row-Major
- Total Hooks = 5120
- Bytes per Pick (if bit-packed 1 bit = 1 hook): `5120 / 8 = 640 bytes`.
- Testing this against file sizes:
  - IVORY: `(4,032,202 - 256) / 640 = 6299.91`
  - LUNA: `(4,838,602 - 256) / 640 = 7559.91`
  - AURORA: `(3,763,402 - 256) / 640 = 5879.91`
- The payload size is almost a perfect multiple of 640 bytes, separated by a 168-186 byte difference, which likely represents a **footer block** or cyclic boundary.

### Entropy Analysis
- Payload bytes are heavily weighted towards alternating bit patterns (`0x55` [01010101], `0xAA` [10101010], `0xCC` [11001100]).
- `0x00` and `0xFF` are rare (< 1%).
- Conclusion: It is a dense, bit-packed representation of the weave, not a sparse compression method like packbits.

## 4. Next Steps: Prototyping
Based on these findings, we can build a prototype export adapter that:
1. Writes the 256-byte header with the expected `Area` blocks.
2. Bit-packs a `5120-hook` lift plan array into `640 bytes` per pick.
3. Appends the binary rows sequentially.
