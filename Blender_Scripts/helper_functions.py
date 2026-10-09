import bpy

# Loop through all actions and enable Fake User
#for action in bpy.data.actions:
#    action.use_fake_user = False
#    track = obj.animation_data.nla_tracks.new()
#    track.strips.new(action.name, int(action.frame_range[0]), action)

#for obj in bpy.context.scene.objects:
#    if obj.animation_data is not None:
#        action = obj.animation_data.action
#        if action is not None:
#            track = obj.animation_data.nla_tracks.new()
#            track.strips.new(action.name, int(action.frame_range[0]), action)
#            obj.animation_data.action = None
#            print('done')

def clean_actions(action_names = None):
    for action in bpy.data.actions:
        if action_names:
            if action.name in action_names:
                bpy.data.actions.remove(action)
        else:
            bpy.data.actions.remove(action)
   
def push_all_actions():
    for action in bpy.data.actions:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.area.type = 'DOPESHEET_EDITOR'

        bpy.context.space_data.ui_mode = 'ACTION'
        bpy.context.selected_objects[0].animation_data.action = action
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.area.type = 'DOPESHEET_EDITOR'

        bpy.context.space_data.ui_mode = 'ACTION'
        bpy.ops.action.push_down()
  
def clear_nla():
    # Iterate through all selected objects
    for obj in bpy.context.selected_objects:
        # Check if the object has animation data
        if obj.animation_data:
            # Loop through tracks backwards to avoid indexing issues while deleting
            for track in reversed(obj.animation_data.nla_tracks):
                obj.animation_data.nla_tracks.remove(track)

clear_nla()
clean_actions()
        
#merged_actions = ['Attack1F', 'AttackHi4F', 'AttackLw4F', 'AttackS4F', 'AttackS3F']
#clean_actions(merged_actions)

#push_all_actions()