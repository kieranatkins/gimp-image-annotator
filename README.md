# gimp-image-annotator
*A GIMP plug-in to allow for direct generation of instance segementation masks for use in machine learning projects, using the power of the GIMP selection tools.*

<h2>Installation</h2>

Follow the guide here: https://en.wikibooks.org/wiki/GIMP/Installing_Plugins to find how to install GIMP plug-ins on your system, save the file `image-annotator.py` in GIMP's plug-in folder.

<h4>Requirements</h4>

* GIMP
* Gtk2
* Python2
   * PyGtk

<h2>How to</h2>

Once installed, navigate to *Toolbox* then *Image Annotator*, add the labels you want, select one, use GIMP's selection tools (a guide can be found here: https://docs.gimp.org/en/gimp-tools-selection.html) to select an area (use Quick Mask or Shift+Q to quickly see the mask you have created). **Make sure antialisaing and feathering is off, you cannot turn it off for rectangle select however it doesn't use it**. Once you have your desired selected area, press *Save selected mask*. Repeat until all areas are selected (be aware, if you save a new selection that covers a previous selection it **will** be overwritten). When finished press *Export files & quit*, where *mask* and *annotations* folders will be created in the working directory and each saved there.

<h4>What is saved?</h4>

*gimp-image-annotator* saves a mask where the values within the associated json file, relate to the value of the mask. The mask is 3 colour channels, however each colour channel is the same therefore they can be dismissed when inputted, choosing any of the channels. An interpretation of the of the selection box is also saved as a svg path, this may be used or may not, it is not essential to the core functionality.

<h4>How do I use the data?</h4>

The annotation data can be inputted using standard JSON parsing libraries, in Python this is `import json` where it will be loaded as a `dict()`. The structure of the annotation files are as follows:

````    JSON
    {
      "regions": {
        "1" : "label",
        "2" : "label",
        ...
      },
      "paths": { 
        "1" : "...",
        "2" : "...",
        ...
       },
       "image" : "image_filename.png",
       "mask" : "image_filename_mask.png"
    }
````



The masks can be inputted using most image processing software. For example in `opencv-python` it would be:


````    Python
    import cv2
    mask = cv2.imread(PATH, cv2.IMREAD_GRAYSCALE)
````

<h2>To do</h2>

- [X] Implement deletion of region masks from displayed list.
- [ ] Implement GIMP's undo feature so that masks are removed from the layer and the toolbox simultaniosuly / deactive undo within this software if not possible.
