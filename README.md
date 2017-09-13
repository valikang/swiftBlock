# SwiftBlock
Blender addon for creating blockMeshDict files for OpenFOAM's blockMesh application. Compatible with Blender 3D 2.76 ->, OpenFOAM 5.0 -> and NumPy 1.13->

## New features:
* The SwiftBlock panel has moved from the properties panel to the tools panel
* The block structure is saved and therefore the time consuming block detection algorithm is only required when the block structure is changed
* The blocks are listed in the SwiftBlock panel
* Blocks can be selected, disabled and enabled interactively from the list
* Blocks can be searched from the current mesh selection
* Number of cells are defined instead of the maximum cell size
* The parallel edges of an edge can be selected easily
* The edge directions visualization
* The new projection vertices, edges and faces to surfaces has been implemented
* The projections are listed in the panel
* The projections can be selected and removed from the list
* Show/hide internal faces to make projections on them
* The automatic snapping algorithm can also be selected
* Extrude blocks operator which preserves internal edges and faces (ALT+E opens the extrude menu)
* Faster block detection with Numba

## How to install Blender, NumPy and SwiftBlock on Ubuntu
```bash
sudo apt install blender
sudo apt install python3-pip
pip install numpy
mkdir -p $HOME/.config/blender/2.xx/scripts/addons
cd $HOME/.config/blender/2.xx/scripts/addons
git clone https://github.com/flowkersma/swiftBlock/
```
Replace 2.xx with your Blender version. Load your OpenFOAM environment and launch Blender. In Blender open the preferences (File->User Preferences). Click on addons tab, search for SwiftBlock and enable it. 

Happy meshing!
