import bpy

def merge_actions_and_push_to_nla(obj, action_names, merged_name="MergedAction"):
    if not obj or (obj.type != 'MESH' and obj.type != 'ARMATURE'):
        return

    # Create a new master action
    merged_action = bpy.data.actions.new(name=merged_name)
    current_frame_offset = 0

    for name in action_names:
        action = bpy.data.actions.get(name)
        if not action:
            continue

        # Copy F-Curves from source action to merged action
        for fcurve in action.fcurves:
            # Find or create corresponding F-Curve in the merged action
            merged_fcurve = merged_action.fcurves.find(fcurve.data_path, index=fcurve.array_index)
            if not merged_fcurve:
                merged_fcurve = merged_action.fcurves.new(data_path=fcurve.data_path, index=fcurve.array_index)

            # Total number of keyframes in this curve
            num_keyframes = len(fcurve.keyframe_points)

            # Copy keypoints with the frame offset
            for i, kp in enumerate(fcurve.keyframe_points):
                new_kp = merged_fcurve.keyframe_points.insert(
                    frame=kp.co[0] + current_frame_offset,
                    value=kp.co[1]
                )
                
                # If it's the LAST keyframe of this sub-action, make it CONSTANT to block blending
                if i == num_keyframes - 1:
                    new_kp.interpolation = 'CONSTANT'
                else:
                    # Otherwise, preserve its original interpolation (Bezier, Linear, etc.)
                    new_kp.interpolation = kp.interpolation

        # Update offset based on the length of the action just added
        if action.frame_range[1] > 0:
            current_frame_offset += (action.frame_range[1] - action.frame_range[0]) + 1

    # Assign the merged action to the object
    if not obj.animation_data:
        obj.animation_data_create()

    obj.animation_data.action = merged_action

    # Push to NLA stack
    track = obj.animation_data.nla_tracks.new()
    track.name = merged_name
    track.strips.new(merged_action.name, int(merged_action.frame_range[0]), merged_action)

    # Clear the active action so it only plays from the NLA
    obj.animation_data.action = None


# Example Usage:
actions_to_merge = {
    'SpecialHiF2': ['SpecialHi', 'SpecialHiCatch', 'SpecialHiThrow', 'FallSpecial', 'LandingFallSpecial'],
    'SpecialAirHiF2': ['SpecialAirHi', 'SpecialHiCatch', 'SpecialHiThrow', 'FallSpecial', 'LandingFallSpecial']
}

for action_name, sub_actions in actions_to_merge.items():
    merge_actions_and_push_to_nla(bpy.context.active_object, sub_actions, action_name)
