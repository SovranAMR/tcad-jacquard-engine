#!/usr/bin/env python3
"""JC5 Format Reverse Engineering — Comprehensive Binary Analysis"""

import os
import struct
import sys

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'samples', 'jc5')


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def analyze_all():
    files = sorted(f for f in os.listdir(SAMPLES_DIR) if f.endswith('.jc5'))
    data = {}
    for f in files:
        data[f] = read_file(os.path.join(SAMPLES_DIR, f))

    print("=" * 80)
    print("  JC5 FORMAT REVERSE ENGINEERING — BINARY ANALYSIS")
    print("=" * 80)

    # ── A) FILE SIZE TABLE ──
    print("\n─── A) DOSYA BOYUT TABLOSU ───")
    print(f"{'Dosya':<35} {'Boyut':>12} {'Boyut/2688':>12}")
    print("-" * 60)
    for f in files:
        size = len(data[f])
        ratio = size / 2688
        print(f"{f:<35} {size:>12,} {ratio:>12.1f}")

    # ── B) HEADER ANALYSIS (first 512 bytes) ──
    print("\n─── B) HEADER ANALİZİ (ilk 512 byte) ───")

    # Check common prefix
    all_headers = [data[f][:512] for f in files]
    common_len = 0
    for i in range(min(len(h) for h in all_headers)):
        vals = set(h[i] for h in all_headers)
        if len(vals) == 1:
            common_len = i + 1
        else:
            break

    print(f"  Ortak prefix uzunluğu: {common_len} byte")
    if common_len > 0:
        print(f"  Ortak prefix hex: {data[files[0]][:min(common_len, 64)].hex()}")

    # First file detailed header
    sample = data[files[0]]
    print(f"\n  İlk dosya ({files[0]}) header hexdump:")
    for offset in range(0, min(256, len(sample)), 16):
        hex_part = ' '.join(f'{sample[offset+i]:02x}' for i in range(16)
                           if offset+i < len(sample))
        ascii_part = ''.join(chr(sample[offset+i])
                            if 32 <= sample[offset+i] < 127 else '.'
                            for i in range(16) if offset+i < len(sample))
        print(f"  {offset:04x}: {hex_part:<48} {ascii_part}")

    # ── C) ASCII STRING EXTRACTION ──
    print("\n─── C) ASCII STRING ÇIKARMA ───")
    for f in files[:3]:  # First 3 files
        strings = extract_ascii_strings(data[f], min_len=4)
        print(f"\n  {f} ({len(strings)} string bulundu):")
        for s_offset, s_text in strings[:30]:
            print(f"    @{s_offset:06x}: {s_text[:80]}")

    # ── D) METADATA BLOCK SEARCH ──
    print("\n─── D) METADATA BLOCK ARAMA ───")
    keywords = [b'Area', b'area', b'hook', b'Hook', b'pick', b'Pick',
                b'width', b'Width', b'height', b'Height',
                b'Generated', b'Version', b'version',
                b'Staubli', b'staubli', b'Bonas', b'bonas',
                b'JC5', b'jc5', b'LUNA', b'OPALE', b'IVORY',
                b'AURORA', b'CRISTAL', b'ZEPHYR', b'CELESTE', b'VELOUR',
                b'repeat', b'Repeat', b'density', b'Density',
                b'warp', b'Warp', b'weft', b'Weft',
                b'color', b'Color', b'design']
    for f in files[:4]:
        print(f"\n  {f}:")
        for kw in keywords:
            positions = find_all(data[f], kw)
            if positions:
                for pos in positions[:3]:
                    ctx = data[f][max(0,pos-8):pos+len(kw)+32]
                    ctx_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
                    print(f"    '{kw.decode()}' @ 0x{pos:06x}: ...{ctx_str}...")

    # ── E) DIFF ANALYSIS (20cm vs 40cm) ──
    print("\n─── E) DIFF ANALİZİ (20cm vs 40cm) ───")
    pairs = [
        ('VRSLS-1-LUNA20CM.jc5', 'VRSLS-1-LUNA40CM.jc5'),
        ('VRSLS-1-OPALE20CM.jc5', 'VRSLS-1-OPALE40CM.jc5'),
        ('VRSLS-1-IVORY20CM.jc5', 'VRSLS-1-IVORY40CM.jc5'),
    ]
    for f1, f2 in pairs:
        if f1 in data and f2 in data:
            d1, d2 = data[f1], data[f2]
            if len(d1) == len(d2):
                diffs = []
                for i in range(len(d1)):
                    if d1[i] != d2[i]:
                        diffs.append(i)
                print(f"\n  {f1} vs {f2}:")
                print(f"    Boyut: {len(d1):,} = {len(d2):,} (aynı)")
                print(f"    Farklı byte sayısı: {len(diffs)}")
                if diffs:
                    print(f"    İlk fark offseti: 0x{diffs[0]:06x}")
                    print(f"    Son fark offseti: 0x{diffs[-1]:06x}")
                    # Show diff clusters
                    clusters = cluster_offsets(diffs)
                    print(f"    Fark kümeleri ({len(clusters)}):")
                    for start, end, count in clusters[:10]:
                        ctx1 = d1[start:min(start+16, len(d1))].hex()
                        ctx2 = d2[start:min(start+16, len(d2))].hex()
                        print(f"      0x{start:06x}-0x{end:06x} ({count} byte)")
                        print(f"        F1: {ctx1}")
                        print(f"        F2: {ctx2}")
            else:
                print(f"\n  {f1} ({len(d1):,}) vs {f2} ({len(d2):,}): FARKLI BOYUT")

    # ── F) SAME-SERIES DIFF ──
    print("\n─── F) AYNI SERİ FARKLI DESEN ───")
    series_pairs = [
        ('VRSLS-2-AURORA.jc5', 'VRSLS-2-CRISTAL.jc5'),
        ('VRSLS-2-AURORA.jc5', 'VRSLS-2-ZEPHYR.jc5'),
        ('VRSLS-3-CELESTE.jc5', 'VRSLS-3-VELOUR.jc5'),
    ]
    for f1, f2 in series_pairs:
        if f1 in data and f2 in data:
            d1, d2 = data[f1], data[f2]
            min_len = min(len(d1), len(d2))
            common_header = 0
            for i in range(min_len):
                if d1[i] != d2[i]:
                    break
                common_header = i + 1
            print(f"\n  {f1} ({len(d1):,}) vs {f2} ({len(d2):,}):")
            print(f"    Ortak header: {common_header} byte (0x{common_header:06x})")

    # ── G) STRUCTURAL HYPOTHESIS ──
    print("\n─── G) YAPI HİPOTEZİ ───")

    # Check if file size relates to picks * ceil(hooks/8)
    print("  Boyut analizi (hooks=2688 varsayımı):")
    hooks = 2688
    bytes_per_pick = hooks // 8  # = 336 bytes per pick if bit-packed
    for f in files:
        size = len(data[f])
        # Try different header sizes
        for hdr in [0, 64, 128, 256, 512, 1024, 2048, 4096]:
            payload = size - hdr
            if payload > 0 and payload % bytes_per_pick == 0:
                picks = payload // bytes_per_pick
                print(f"    {f}: header={hdr}, payload={payload:,}, "
                      f"picks={picks} (@{hooks} hooks, bit-packed)")
                break
        else:
            # Try byte-per-hook
            for hdr in [0, 64, 128, 256, 512, 1024, 2048]:
                payload = size - hdr
                if payload > 0 and payload % hooks == 0:
                    picks = payload // hooks
                    print(f"    {f}: header={hdr}, payload={payload:,}, "
                          f"picks={picks} (@{hooks} hooks, byte-per-hook)")
                    break
            else:
                # Try common hook counts
                for h in [1344, 2688, 5376, 10752]:
                    bpp = h // 8
                    for hdr in range(0, 8192, 2):
                        payload = size - hdr
                        if payload > 0 and payload % bpp == 0:
                            picks = payload // bpp
                            if 100 <= picks <= 50000:
                                print(f"    {f}: header={hdr}, hooks={h}, "
                                      f"picks={picks}, bit-packed")
                                break
                    else:
                        continue
                    break

    # ── H) PAYLOAD ENTROPY AND PATTERN ──
    print("\n─── H) PAYLOAD ENTROPİ VE DESEN ANALİZİ ───")
    sample = data[files[0]]
    # Check byte value distribution in last 4096 bytes
    tail = sample[-4096:]
    counts = [0] * 256
    for b in tail:
        counts[b] += 1
    top5 = sorted(enumerate(counts), key=lambda x: -x[1])[:5]
    print(f"  {files[0]} — son 4096 byte değer dağılımı:")
    for val, cnt in top5:
        print(f"    0x{val:02x} ({val:3d}): {cnt} kez ({cnt/4096*100:.1f}%)")

    # Check if it's mostly 0x00 and 0xFF (bit-packed binary)
    zero_pct = counts[0] / 4096 * 100
    ff_pct = counts[0xFF] / 4096 * 100
    print(f"  0x00: {zero_pct:.1f}%, 0xFF: {ff_pct:.1f}%")
    if zero_pct + ff_pct > 60:
        print(f"  → YÜKSEK ihtimal: bit-packed binary (sparse pattern)")


def extract_ascii_strings(data, min_len=4):
    """Extract printable ASCII strings."""
    strings = []
    current = []
    start = 0
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if not current:
                start = i
            current.append(chr(b))
        else:
            if len(current) >= min_len:
                strings.append((start, ''.join(current)))
            current = []
    return strings


def find_all(data, pattern):
    positions = []
    start = 0
    while True:
        pos = data.find(pattern, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    return positions


def cluster_offsets(offsets, gap=16):
    if not offsets:
        return []
    clusters = []
    start = offsets[0]
    prev = offsets[0]
    count = 1
    for o in offsets[1:]:
        if o - prev <= gap:
            count += 1
        else:
            clusters.append((start, prev, count))
            start = o
            count = 1
        prev = o
    clusters.append((start, prev, count))
    return clusters


if __name__ == '__main__':
    analyze_all()
