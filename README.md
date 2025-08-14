# TAMSVIZ - Visualization and Annotation Tool for ROS

![](screenshots/1.png)

### Features
#### Added Features for Behavior Annotation using Videos
- Customizable labels for timeline annotations (easily input text to spans using Tkinter Interface)
- Config file to point to the addon

### Building & Running the Addon
- mkdir -p ztamsviz2_ws/src # works with what is currently in the config files, change as needed
- cd ztamsviz2_ws/src
- git clone https://github.com/zulkafilabbas/tamsviz
- cd ..
- catkin_make -j1 # slow, but prevents crashes while building on older machines
- source devel/setup.bash
- roslaunch tamsviz tamsviz.launch
- Create an annotation track
- Create a span on the track
- Double right click should bring up the interface, select and cllick submit
- The document file for your rosbag stores your labels
- TODO: Add the label parser for tmv file

### Debugging Info.
If the interface does not launch, check python version (requires >= python 3.8), bashrc (correct paths to workspace ztamsviz2_ws added?), config files (both the tamavis_addon_config.json (which points to the label_selector2.py script) and the tamsviz/CMakeLists.txt - should copy the right files, currently set to label_selector2.py and label_selector_config2.json, can do sanity checks by directly launching the interface, and the tamsviz executable in the devel/lib/ folder after compiling if all else fails.)

### Stability Notes
- Tested on Ubuntu 20.04, ROS Noetic, Python 3.8, Moveit for ROS Noetic 
- Tested on machines with Nvidia 2060, 1650, nvidia drivers 535
- Having no Nvidia drivers installed seemed to crash the GUI when resizing elements.
- Known to crash every now and then, just because! Save your work regularly.

#### Original Features
- Visualize robots and robot trajectories
- Visualize rosbags
- Annotate rosbags
- Annotate images
- Undo/redo
- Visualization markers, interactive markers
- Creating interactive markers without writing code
- Loading and playing rosbags
- Seeking in rosbags with multiple TF publishers, without breaking TF
- Online visualization
- Plots, filtering plot data, message queries
- Physically-based shading
- Dynamic lighting and shadows
- Transparency without order inversion
- Options to fix mesh normals
- Normal mapping
- Multi-threaded architecture, renderer can't freeze GUI
- Asynchronous loading, asynchronous rendering
- High-quality text rendering
- Anti-aliasing
- ROS integration
- Mouse picking

### Documentation
https://tams-group.github.io/tamsviz/
