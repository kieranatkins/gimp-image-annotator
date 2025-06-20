# gimp-image-annotator
*gimp-image-annotator or GIÀ, a lightweight GIMP plug-in to alllow for computer vision-assisted image annotation using the powerful GIMP selection toolbox.*

<p align="center">
  <img src="https://github.com/kieranatkins/gimp-image-annotator/blob/main/anim.gif" />
</p>


<h2>Installation</h2>

Follow the guide here: https://en.wikibooks.org/wiki/GIMP/Installing_Plugins to find how to install GIMP plug-ins on your system, save the file `image-annotator.py` in GIMP's plug-in folder. 

Updated for GIMP v3! In this version of GIMP, all plug-ins must be placed in a directory of their own with the same name as the plug-in in order to be parsed by the program. Therefore, the `image-anntotaor.py` file must be placed inside a folder named `image-annotator` inside the plug-in directory. On Linux, the plug-in may need to be made executable with the command `chmod a+x /path/to/image-annotator.py` in order to be seen by GIMP.

<h2>Using the software</h2>

Once installed, navigate to *Annotation* then *GIMP Image Annotator (GIÀ)*, add the labels you want, select one, use GIMP's selection tools (e.g. The Fuzzy Select tool - a guide can be found here: https://docs.gimp.org/en/gimp-tools-selection.html) to select an area (use Quick Mask or Shift+Q to quickly see the mask you have created). **Make sure antialisaing and feathering is off, you cannot turn it off for rectangle select however it isn't used**. Once you have your desired selected area, press *Save mask*. Repeat until all objects are annotated.

<h4>How do I use the data?</h4>

*gimp-image-annotator* saves a binary mask of each annotation, with class of mask stored in the `_annotations.json` file. The `_annotations.json` file is structured as followed


````    JSON
    [{
      "label": "label",
      "id": "0",
      "filename": "image.png"
    }]
````

The masks can be inputted using most image processing software. For example in `opencv-python` it would be:


````    Python
    import cv2
    mask = cv2.imread(PATH, cv2.IMREAD_GRAYSCALE)
````
