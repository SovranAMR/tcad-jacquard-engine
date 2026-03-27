"""Dosya I/O — .tcad zip formatı ve PNG import/export."""

import zipfile
import json
import io
import os
import tempfile
import numpy as np
from PIL import Image


def save_project(doc, path):
    """Projeyi endüstriyel .tcad (zip) formatında kaydeder."""
    meta = {
        'w': doc.width,
        'h': doc.height,
        'rx': doc.repeat_x,
        'ry': doc.repeat_y,
        'pal': doc.palette,
        'hook_count': doc.hook_count,
        'weave_phases': doc.weave_phases,
    }
    buf = io.BytesIO()
    np.save(buf, doc.grid)

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('meta.json', json.dumps(meta))
        zf.writestr('data.npy', buf.getvalue())

        # Region mask
        rm_buf = io.BytesIO()
        np.save(rm_buf, doc.region_mask)
        zf.writestr('region_mask.npy', rm_buf.getvalue())

    doc.file_path = path
    doc.is_dirty = False


def load_project(doc, path):
    """Projeyi .tcad formatından yükler."""
    with zipfile.ZipFile(path, 'r') as zf:
        meta = json.loads(zf.read('meta.json'))
        buf = io.BytesIO(zf.read('data.npy'))

        doc.width = meta['w']
        doc.height = meta['h']
        doc.repeat_x = meta.get('rx', 1)
        doc.repeat_y = meta.get('ry', 1)
        doc.palette = [tuple(c) for c in meta['pal']]
        doc.hook_count = meta.get('hook_count', 2688)
        doc.weave_phases = meta.get('weave_phases', {})
        doc.grid = np.load(buf)

        # Strict Shape Validation Guard: Meta vs Actual Grid
        gh, gw = doc.grid.shape[:2]
        if gh != doc.height or gw != doc.width:
            raise ValueError(
                f"🚨 RED TEAM GUARD: Dosya bütünlüğü bozuk! "
                f"Metadata {doc.width}x{doc.height} beyan ediyor, "
                f"fakat gerçek matris verisi {gw}x{gh} boyutunda. "
                f"Kötü niyetli/bozuk dosya reddedildi."
            )

        # Region mask
        if 'region_mask.npy' in zf.namelist():
            rm_buf = io.BytesIO(zf.read('region_mask.npy'))
            doc.region_mask = np.load(rm_buf)
            rh, rw = doc.region_mask.shape[:2]
            if rh != doc.height or rw != doc.width:
                new_rm = np.zeros((doc.height, doc.width), dtype=np.uint8)
                mh, mw = min(rh, doc.height), min(rw, doc.width)
                new_rm[:mh, :mw] = doc.region_mask[:mh, :mw]
                doc.region_mask = new_rm
        else:
            doc.region_mask = np.zeros((doc.height, doc.width), dtype=np.uint8)

    doc.file_path = path
    doc.is_dirty = False


def export_png(doc, path):
    """Endüstriyel makine yazılımlarının istediği 8-bit P Mode çıktı."""
    img = Image.fromarray(doc.grid, mode='P')
    pal = []
    if doc.is_technical:
        pal.extend([255, 255, 255])
        for _ in range(255):
            pal.extend([0, 0, 0])
    else:
        for c in doc.palette:
            pal.extend(c)
        while len(pal) < 768:
            pal.extend([0, 0, 0])
    img.putpalette(pal)
    img.save(path)


def import_image(doc, path):
    """RGB imajlar 256 renk endüstri standardına kuantize edilir."""
    img = Image.open(path).convert('RGB')
    img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    doc.grid = np.array(img, dtype=np.uint8)
    doc.width = doc.grid.shape[1]
    doc.height = doc.grid.shape[0]

    pal = img.getpalette()
    doc.palette = []
    for i in range(256):
        if pal and i * 3 + 2 < len(pal):
            doc.palette.append((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]))
        else:
            doc.palette.append((128, 128, 128))

    doc.region_mask = np.zeros((doc.height, doc.width), dtype=np.uint8)
    doc.file_path = None
    doc.is_dirty = True


def import_jc5(doc, path):
    """JC5 Makine dosyasını (örgü çıktısı) siyah-beyaz grid olarak yükler."""
    with open(path, 'rb') as f:
        data = f.read()
        
    # JC5 analizine göre header 256 byte
    payload = data[256:]
    
    target_hooks = 5120
    bpp = 640  # 5120 / 8
    
    picks = len(payload) // bpp
    
    raw_payload = payload[:picks * bpp]
    
    # Bitleri numpy array e çeviriyoruz
    packed_array = np.frombuffer(raw_payload, dtype=np.uint8).reshape((picks, bpp))
    unpacked = np.unpackbits(packed_array, axis=1)
    
    doc.grid = unpacked.astype(np.uint8)
    doc.width = target_hooks
    doc.height = picks
    doc.hook_count = target_hooks
    
    doc.region_mask = np.zeros((picks, target_hooks), dtype=np.uint8)
    
    doc.palette = [(220, 220, 220), (30, 30, 30)]  # 0: gri-beyaz, 1: koyu gri
    while len(doc.palette) < 256:
        doc.palette.append((128, 128, 128))
        
    doc.file_path = None
    doc.is_dirty = True

