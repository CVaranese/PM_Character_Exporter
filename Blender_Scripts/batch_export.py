import bpy
import os

# export_list = None
# export_list = ['Attack1F', 'AttackHi4F', 'AttackLw4F', 'AttackS4F', 'AttackS3F']
export_list = None

# 1. CONFIGURE YOUR SETTINGS
# Ensure the path ends with a double slash or forward slash
export_path = r"D:\\ROA2_Modding\\character_data\\Captain_falcon\\p+falcon\\exported_animations\\" 
file_format = "FBX" # Change to "GLTF" or "OBJ" if needed
anim_prefix = 'AN_Cap_'

# 2. ISOLATE THE ARMATURE
# Assumes the active object is the armature
obj = bpy.context.active_object
if not obj or obj.type != 'ARMATURE':
    raise ValueError("Please select an Armature as the active object.")

if not obj.animation_data:
    obj.animation_data_create()

# 3. STASH ALL ACTIONS ONTO NLA TRACKS
adt = obj.animation_data

# Clear existing tracks to prevent duplicates
#adt.nla_tracks.clear()

for action in bpy.data.actions:
    if export_list and action.name not in export_list:
        continue
    # Set the active action to evaluate it
    adt.action = action
    
    # Push the active action down to a new NLA track
    track = adt.nla_tracks.new()
    track.name = action.name
    track.strips.new(action.name, int(action.frame_range[0]), action)

# Clear the main action so NLA tracks control the skeleton fully
adt.action = None

# 4. BATCH EXPORT
if not os.path.exists(export_path):
    os.makedirs(export_path)

# Mute all tracks first so we can activate them one by one
for track in adt.nla_tracks:
    track.mute = True

for track in adt.nla_tracks:
    # Skip action if not specified
    if export_list and track.name not in export_list:
        continue
    
    # Unmute the track we want to export
    track.mute = False
    
    # Define file paths
    file_name = f"{anim_prefix}{track.name}.{file_format.lower()}"
    full_path = os.path.join(export_path, file_name)
    
    # Select only the target object for export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    # Execute Export (Example for FBX. Adjust parameters per your requirements)
    if file_format == "FBX":
        bpy.ops.export_scene.fbx(
            filepath=full_path, 
            use_selection=True,
            add_leaf_bones=False,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            path_mode='AUTO',
            object_types={'ARMATURE', 'OTHER'}
        )
    elif file_format == "GLTF":
        bpy.ops.export_scene.gltf(
            filepath=full_path, 
            export_format='GLB', 
            use_selection=True
        )
    
    # Mute the track again for the next loop
    track.mute = True

print("Batch export complete!")