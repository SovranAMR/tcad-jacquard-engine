"""Machine Export Adapters — Tezgah format çıktıları ve plugin sistemi."""

import os
import struct
import numpy as np
from abc import ABC, abstractmethod

from tcad.constraints import LoomProfile, ConstraintEngine


class BaseMachineAdapter(ABC):
    """Farklı tezgah üreticileri için ana adaptör arayüzü."""

    @property
    @abstractmethod
    def profile(self) -> LoomProfile:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def extension(self) -> str:
        pass

    def can_export(self, doc) -> tuple[bool, list]:
        """Export öncesi uyumluluk kontrolü."""
        can_exp, errors, warns, infos = ConstraintEngine.is_export_ready(
            doc, self.profile)
        return can_exp, errors

    @abstractmethod
    def export(self, doc, machine_plan: np.ndarray, filepath: str) -> dict:
        """Export işlemini gerçekleştirir. Metadata raporu döndürür."""
        pass


class GenericInternalAdapter(BaseMachineAdapter):
    """Şirket içi AR-GE ve testler için bit-packed genel format."""

    def __init__(self):
        self._profile = LoomProfile(
            name="Generic Lab Loom",
            max_hooks=2688,
            supports_split=True,
            max_sections=4
        )

    @property
    def profile(self):
        return self._profile

    @property
    def name(self):
        return "Generic Internal Binary"

    @property
    def extension(self):
        return ".bin"

    def export(self, doc, machine_plan: np.ndarray, filepath: str) -> dict:
        can_exp, errors = self.can_export(doc)
        if not can_exp:
            raise ValueError(f"Export reddedildi: {errors[0]['message']}")

        picks, hooks = machine_plan.shape
        files_written = []

        if hooks > self.profile.max_hooks:
            parts = int(np.ceil(hooks / self.profile.max_hooks))
            base, ext = os.path.splitext(filepath)
            for i in range(parts):
                start = i * self.profile.max_hooks
                end = min(start + self.profile.max_hooks, hooks)
                out_path = f"{base}_HEAD{i + 1}{ext}"
                self._write_binary(machine_plan[:, start:end], out_path)
                files_written.append(out_path)
            note = f"Desen {parts} kafaya bölündü."
        else:
            self._write_binary(machine_plan, filepath)
            files_written.append(filepath)
            note = "Tek kafa export başarılı."

        return {
            'adapter': self.name,
            'files': files_written,
            'note': note,
            'picks': picks,
            'hooks': hooks,
        }

    def _write_binary(self, plan: np.ndarray, path: str):
        picks, hooks = plan.shape
        rem = hooks % 8
        if rem != 0:
            plan = np.pad(plan, ((0, 0), (0, 8 - rem)), constant_values=0)
        packed = np.packbits(plan, axis=1, bitorder='big')

        with open(path, 'wb') as f:
            f.write(b'TCAD_GENERIC_V5\x00')
            f.write(struct.pack('<II', picks, hooks))
            f.write(packed.tobytes())


class StaubliJC5Adapter(BaseMachineAdapter):
    """Gerçek JC5 formatı export adaptörü (Reverse-Engineered)."""

    def __init__(self):
        # JC5 Reverse-Engineering bazlı profil
        self._profile = LoomProfile(
            name="Staubli JC5 (5120 Hooks)",
            max_hooks=5120,
            supports_split=False,
            max_sections=1
        )

    @property
    def profile(self):
        return self._profile

    @property
    def name(self):
        return "Staubli JC5 (Experimental)"

    @property
    def extension(self):
        return ".jc5"

    def export(self, doc, machine_plan: np.ndarray, filepath: str) -> dict:
        can_exp, errors = self.can_export(doc)
        if not can_exp:
            raise ValueError(f"JC5 Export reddedildi: {errors[0]['message']}")

        picks, original_hooks = machine_plan.shape

        # JC5 Reverse-Engineering: 5120 total hooks constant for this footprint
        # 3 Areas: 32 + 288 + 4800 = 5120
        target_hooks = 5120
        
        # Pad or truncate to exactly 5120 hooks
        if original_hooks < target_hooks:
            padded_plan = np.zeros((picks, target_hooks), dtype=np.uint8)
            # Center the pattern in the 4800-hook main area (offset 320)
            main_area_offset = 320
            w = min(original_hooks, 4800)
            padded_plan[:, main_area_offset:main_area_offset+w] = machine_plan[:, :w]
            plan_to_export = padded_plan
        else:
            plan_to_export = machine_plan[:, :target_hooks]

        # --- RED TEAM: Hardware Blindness Mitigation (Weft Selectors) ---
        # Makineye mekik/iplik değiştirme sinyallerini (Control Picks) enjekte et
        if hasattr(doc, 'weft_seq') and getattr(doc.weft_seq, 'sequence', None):
            colors = doc.weft_seq.generate(picks)
            unique_colors = []
            for c in colors:
                tc = tuple(c)
                if tc not in unique_colors:
                    unique_colors.append(tc)
            
            # Son 8 kancayı (5112 - 5119) Mekiği tetiklemek için kullan
            for row in range(picks):
                tc = tuple(colors[row])
                sel_idx = unique_colors.index(tc)
                if sel_idx < 8:
                    plan_to_export[row, 5112 + sel_idx] = 1

        # Bit-pack: 5120 hooks = 640 bytes per pick
        packed = np.packbits(plan_to_export, axis=1, bitorder='big')
        
        # Build 256-byte header
        header = bytearray(256)
        
        # 0x00-0x17: Binary magic/dimensions
        header[0] = 0x81
        header[1] = 0xFE
        header[2] = 0x01
        header[3] = 0x01
        header[16:21] = b'VRSLS'
        
        # ASCII Metadata @ 0x39
        gen_str = b'Generated with EAT OpenWeave Converter'
        header[0x39:0x39+len(gen_str)] = gen_str
        
        # Area Metadata @ 0x74
        area_str = b' Area 1: 32 hooks    d            Area 2: 288 hooks    d            Area 3: 4800 hooks'
        header[0x74:0x74+len(area_str)] = area_str

        # Pad remainder of header with 0x0F
        for i in range(0x39 + len(gen_str), 0x74):
            header[i] = 0x00
        for i in range(0x74 + len(area_str), 256):
            if header[i] == 0x00:
                header[i] = 0x0F

        with open(filepath, 'wb') as f:
            f.write(header)
            f.write(packed.tobytes())
            
            # Write footer matching the 168-byte remainder found in real files
            f.write(bytes([0x00] * 168))

        return {
            'adapter': self.name,
            'files': [filepath],
            'note': f"JC5 Exported with {target_hooks} hooks structure.",
            'picks': picks,
            'hooks': target_hooks,
        }


class AdapterRegistry:
    """Sistemdeki tüm adaptörleri yönetir."""
    
    _adapters = {
        'generic': GenericInternalAdapter(),
        'jc5': StaubliJC5Adapter(),
    }
    
    @classmethod
    def get_all(cls) -> list[BaseMachineAdapter]:
        return list(cls._adapters.values())
        
    @classmethod
    def get(cls, key: str) -> BaseMachineAdapter:
        if key not in cls._adapters:
            raise KeyError(f"Adapter '{key}' bulunamadı.")
        return cls._adapters[key]
