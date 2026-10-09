"""Read-only: which shield skeleton / physics asset / mesh properties can Python see and set?"""
from pathlib import Path

import unreal

eal = unreal.EditorAssetLibrary
out = []
for path in ("/Game/Characters/Shared/Shield/Animation/SK_VFX_Shield_skeleton",
             "/Game/Characters/Shared/Shield/PH_Cha_Shield",
             "/Game/Characters/Shared/Shield/SK_Cha_Shield"):
    obj = eal.load_asset(path)
    out.append(f"== {path} ({obj.get_class().get_name()})")
    for name in ("preview_skeletal_mesh", "preview_mesh", "skeleton", "physics_asset", "shadow_physics_asset"):
        try:
            v = obj.get_editor_property(name)
            out.append(f"  {name} = {v.get_path_name() if hasattr(v, 'get_path_name') else v}")
        except Exception as e:
            out.append(f"  {name}: n/a ({str(e)[:90]})")
    out.append("  methods: " + ", ".join(m for m in dir(obj) if any(k in m for k in ("preview", "skeleton", "physics"))))
Path(__file__).with_name("probe_report.txt").write_text("\n".join(out) + "\n")
