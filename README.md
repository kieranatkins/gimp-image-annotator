# gimp-image-annotator
*gimp-image-annotator or GIÀ, a lightweight GIMP plug-in to alllow for computer vision-assisted image annotation usig the powerful GIMP selection toolbox.*

<h2>Installation</h2>

Follow the guide here: https://en.wikibooks.org/wiki/GIMP/Installing_Plugins to find how to install GIMP plug-ins on your system, save the file `image-annotator-2.py` in GIMP's plug-in folder.

<h4>Requirements</h4>

* GIMP
* Gtk2
* Python2
   * PyGtk

<h2>How to</h2>

Once installed, navigate to *Toolbox* then *Image Annotator*, add the labels you want, select one, use GIMP's selection tools (a guide can be found here: https://docs.gimp.org/en/gimp-tools-selection.html) to select an area (use Quick Mask or Shift+Q to quickly see the mask you have created). **Make sure antialisaing and feathering is off, you cannot turn it off for rectangle select however it doesn't use it**. Once you have your desired selected area, press *Save selected mask*. Repeat until all areas are selected (be aware, if you save a new selection that covers a previous selection it **will** be overwritten). When finished press *Export files & quit*, where *mask* and *annotations* folders will be created in the working directory and each saved there.


<h4>How do I use the data?</h4>

*gimp-image-annotator* saves a binary mask of each annotation, with class of mask stored in the `_annotations.json` file. The `_annotations.json` file is structured as followed


````    JSON
    [{
      "label": "string"
      "id": "int",
      "filename": "string",
    }]
````

The masks can be inputted using most image processing software. For example in `opencv-python` it would be:


````    Python
    import cv2
    mask = cv2.imread(PATH, cv2.IMREAD_GRAYSCALE)
````

<h2>To do</h2>

- [X] Implement deletion of region masks from displayed list.
- [ ] Implement GIMP's undo feature so that masks are removed from the layer and the toolbox simultaniosuly / deactive undo within this software if not possible.
# License 
This project is released under [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).
