__author__ = "Chris Varanese"
__version__ = "1.0"

from BrawlCrate.NodeWrappers import *
from System.Windows.Forms import ToolStripMenuItem
from mawwwkLib import *

SCRIPT_NAME = "Export to ROA Anim"
VALID_GROUP_NAMES = ["AnmChr(NW4R)"]


## Start enable check functions
# Wrapper: BRRESWrapper
def enableCheckBRES(sender, event_args):
    node = BrawlAPI.SelectedNode
    sender.Enabled = (node and node.HasChildren)

    # Below code causes infinite loop, not sure why.

    # Enable node if it contains AnmChr(NW4R)
    # if node:
    # 	BrawlAPI.ShowMessage('Checked 2 ' + node.Name, "")
    # 	if node.HasChildren:
    # 		sender.Enabled = False
    # 		BrawlAPI.ShowMessage('Has children ' + node.Name, "")
    # 		for group in node.Children:
    # 			BrawlAPI.ShowMessage('Checking ' + group.Name, "")
    # 			if group.Name in VALID_GROUP_NAMES:
    # 				BrawlAPI.ShowMessage('WeWon ' + group.Name, "")
    # 				sender.Enabled = True
    # 				return
    # 	else: 
    # 		sender.Enabled = False
    # else:
    # 	sender.Enabled = False

## End enable check functions
## Start loader functions

# Base loader function (parent chr0 node)
def export_anim(sender, event_args):
    main(BrawlAPI.SelectedNode)

# Main function
def main(bresNode):
    # Select MDL0 for all exports
    file_filter = "MDL0 Model (*.mdl0)|*.mdl0|All files (*.*)|*.*"
    model_name = BrawlAPI.OpenFileDialog("Select the model for anim export", file_filter)
    if model_name == "": 
        return
    model =  NodeFactory.FromFile(None, model_name)
    
    for group in BrawlAPI.SelectedNode.Children:
        if group.Name in VALID_GROUP_NAMES[0]:
            # begin processing
            for chr0_node in group.Children:

                # copy chr0_node to not update in pac
                new_anim = CHR0Node()
                new_anim.Name = chr0_node.Name
                new_anim.FrameCount = chr0_node.FrameCount
                new_anim.Loop = chr0_node.Loop

                # remove TransN bone to avoid issues in the future
                for bone in chr0_node.GetChildrenRecursive():
                    if bone.Name != 'TransN':
                        new_anim.AddChild(bone)

                # rename according to rivals mapping?

                # export animation
                AnimFormat.Serialize(new_anim, f"./animations/{new_anim.Name}.anim", model)
    return

## End loader functions
## Start context menu add

LONG_TEXT = "Remove TransN bones and export all animations"
SHORT_TEXT = "Export all to anim..."

BrawlAPI.AddContextMenuItem(BRESWrapper, "", LONG_TEXT, enableCheckBRES, ToolStripMenuItem(SHORT_TEXT, None, export_anim))