# Porting a P+ Character into Rivals of Aether 2

## Porting the Model

1. Open the model in brawlcrate

2. Export as MD0 and DAE

3. Open in Blender 3.6 (use import dae plugin)

4. Set unit scale to .01, rotate 90 degrees Y, scale 10.33 all axes

5. ctrl-a, apply all transforms to deltas

6. Rename 'ThrowN' bone to 'Grab_M'

7. Export as fbx

## Porting Animations

1. **Export animations from BrawlCrate** using the export script (`export_to_anim.py`). The script will create an `animations/` folder and export all animations into it.

2. **Set framerate to 60 fps** in Blender before importing.

3. *(Optional)* **Clear pre-existing animations** if this is a clean re-import, using the helper functions script.

4. **Import animations into Blender 3.6**, which should already contain your transformed model. Use the Import BrawlBox Animation plugin.

5. **Push all actions to the NLA stack** using the helper functions script.

6. **Merge actions** to match Rivals of Aether 2 conventions (e.g. Jab 1–4 combined into one animation) using `merge_actions.py`.

7. **Export to FBX** using the batch export script (`batch_export.py`). This may take a short time.

8. **Import into Unreal Engine**. Make sure the custom sample rate is set to **60**. This may take a bit.
