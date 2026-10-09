GLOBAL_KB_MULTIPLIER = 3


def calc_rivals2_kb(damage, wdsk, bkb, scaling):
    """
    Convert PM/Brawl knockback params to Rivals 2 BKB and Scaling.

    Args:
        damage:  Move damage value
        wdsk:    Weight-dependent set knockback (None / 0 / "" if not used)
        bkb:     Base knockback
        scaling: Knockback scaling

    Returns:
        (rivals2_bkb, rivals2_scaling)
    """
    if wdsk:
        kb_at_0 = bkb + scaling / 100 * (18 + 1.4 * ((wdsk * 10) / 20 + 1))
        kb_at_100 = kb_at_0
    else:
        kb_at_0 = bkb + scaling / 100 * (18 + (14 * 0 * (damage + 2)) / 200)
        kb_at_100 = bkb + scaling / 100 * (18 + (14 * 100 * (damage + 2)) / 200)

    r2kb_at_0 = kb_at_0 * 0.03 * 10.666
    r2kb_at_100 = kb_at_100 * 0.03 * 10.666

    rivals2_bkb = r2kb_at_0 / GLOBAL_KB_MULTIPLIER
    rivals2_scaling = (
        (r2kb_at_100 / GLOBAL_KB_MULTIPLIER) - (r2kb_at_0 / GLOBAL_KB_MULTIPLIER)
    ) / (100 * 0.12)

    return rivals2_bkb, rivals2_scaling


if __name__ == "__main__":
    # Falcon Bair: Damage=14, WDSK=None, BKB=20, Scaling=100
    # Expected: Rivals 2 BKB=4.05, Rivals 2 Scaling=1.00
    bkb, scaling = calc_rivals2_kb(damage=18, wdsk=None, bkb=24, scaling=100)
    print(f"Rivals 2 BKB: {bkb:.2f}  (expected 4.05)")
    print(f"Rivals 2 Scaling: {scaling:.2f}  (expected 1.00)")
