"""Tahar / Hook Mapping — Çözgü tellerini fiziksel makine kancalarına bağlar."""

import numpy as np


class HookMapping:
    """X ekseni piksellerini fiziksel Jakar Kancalarına bağlar."""

    @staticmethod
    def straight(ends, hooks):
        """Düz Tahar (1->1, 2->2)."""
        return np.arange(ends) % hooks

    @staticmethod
    def pointed(ends, hooks):
        """Aynalı / V Tahar (Ortadan dönen dizilim)."""
        cycle = np.concatenate((np.arange(hooks), np.arange(hooks - 2, 0, -1)))
        return np.resize(cycle, ends)

    @staticmethod
    def apply_fast(lift_plan, mapping, total_hooks):
        """
        Lift planını makine kancalarına dağıtır.
        np.bitwise_or.at ile for döngüsü olmadan devasa RAM hızında kanca ataması.
        Dead hook (-1) değerleri filtrelenir — sessiz veri bozulması engellenir.
        """
        picks, ends = lift_plan.shape
        machine_plan = np.zeros((picks, total_hooks), dtype=np.uint8)

        # Dead hook filtresi: negatif indeksler NumPy'da son elemana wrap yapar
        # Bu sessiz veri bozulmasıdır — kesinlikle engellenmeli
        valid_mask = mapping >= 0
        if not np.any(valid_mask):
            return machine_plan

        valid_mapping = mapping[valid_mask]
        valid_lift = lift_plan[:, valid_mask]

        row_idx = np.arange(picks)[:, None]
        col_idx = valid_mapping[None, :]
        np.bitwise_or.at(machine_plan, (row_idx, col_idx), valid_lift)

        return machine_plan
