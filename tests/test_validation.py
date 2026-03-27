import pytest
import numpy as np
from tcad.validation import ValidationEngine

def create_plain_weave(w, h):
    plan = np.zeros((h, w), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            plan[y, x] = (x + y) % 2
    return plan

def test_auto_fix_floats():
    plan = create_plain_weave(20, 20)
    # Create a 15-length warp float at x=5
    plan[2:17, 5] = 1
    
    # Analyze float errors before
    errs = ValidationEngine.analyze_fabric(plan, max_warp=7, max_weft=7)
    
    fixed_plan, total_fixes = ValidationEngine.auto_fix_floats(plan, max_warp=7, max_weft=7)
    assert total_fixes > 0
    
    errs_after = ValidationEngine.analyze_fabric(fixed_plan, max_warp=7, max_weft=7)
    for e in errs_after:
        if 'Atlama' in e['type'] or 'Float' in e['type']:
            assert e['len'] <= 7

def test_auto_fix_multi_floats():
    plan = create_plain_weave(30, 30)
    plan[0:20, 10] = 1 # 20 length warp
    plan[15, 0:25] = 0 # 25 length weft of 0s
    
    fixed_plan, total_fixes = ValidationEngine.auto_fix_floats(plan, max_warp=7, max_weft=7)
    assert total_fixes >= 2
    
    errs_after = ValidationEngine.analyze_fabric(fixed_plan, max_warp=7, max_weft=7)
    for e in errs_after:
        if 'Atlama' in e['type'] or 'Float' in e['type']:
            assert e['len'] <= 7

