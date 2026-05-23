# Windows usage - double-click scripts

You don't need to type any commands. Just double-click these files,
in this order, the very first time you use the tool.

## First time only

1. Install **Python 3.10+** from https://www.python.org/downloads/
   IMPORTANT: tick "Add Python to PATH" during install.
2. Double-click **1-install.bat**
   (Installs all needed libraries. Takes 5-10 minutes the first time.)

## After that, anytime you want to use the tool

| File | What it does |
|------|--------------|
| **2-open-viewer.bat** | Opens the 3D viewer window. Use *File -> Open* to load a .adv file. |
| **3-convert-file.bat** | Convert ONE .adv file to .obj / .stl. Drag the .adv into the window when asked. |
| **4-convert-folder.bat** | Convert ALL .adv files inside a folder. Drag the folder into the window when asked. |
| **5-show-file-info.bat** | Just print what is inside a .adv file (metadata, solutions, etc). |

The converted .obj / .stl files appear in:
- `windows\output\`        (from script 3)
- `windows\output_batch\`  (from script 4)

You can open .obj files with:
- The built-in Windows 3D Viewer app (right-click .obj -> Open with -> 3D Viewer)
- The online viewer at https://3dviewer.net (drag-and-drop the .obj)
- MeshLab, Blender, FreeCAD, or any other 3D software
