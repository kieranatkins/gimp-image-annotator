#!/usr/bin/env python

from gimpfu import *
import gtk
import gobject
import gimpcolor
import os
import json
import errno

class IAWindow(gtk.Window):

    def __init__(self, img, layer, *args):
        NAME = 'Image Annotator'
        self.running = False

        # stores the filepath of the current gimp image
        self.img = img

        # layer holding the annotation mask
        self.annot_layer = layer

        # initialise the window
        win = gtk.Window.__init__(self, *args)
        self.set_title(NAME)
        self.set_border_width(10)

        # Obey the window manager quit signal:
        self.connect("destroy", self.reset_and_quit)

        # The main layout, holds all other layouts
        main_vbox = gtk.VBox(spacing=8)

        # Add the main layout to the Window (self)
        self.add(main_vbox)

        # Create and add label denoting label creation section
        new_label_label = gtk.Label('Label creation')
        main_vbox.pack_start(new_label_label, False, False, 0)

        # Create and add text entry box for labels
        self.add_label_entry = gtk.Entry()
        main_vbox.pack_start(self.add_label_entry, False, False, 2)
        
        # Create and add 'add label button'
        add_label_val_btn = gtk.Button('Add label value')
        # Connect add_label_on_click function to the clicking of the add_label button
        add_label_val_btn.connect("clicked", self.add_label_on_click)
        main_vbox.pack_start(add_label_val_btn, False, False, 2)

        # Add section seperator (no functionality, only aesthetics)
        hseperator_1 = gtk.HSeparator()
        main_vbox.pack_start(hseperator_1, False, False, 2)

        # Create and add 'Mask creation' label
        add_label_label = gtk.Label('Mask creation')
        main_vbox.pack_start(add_label_label, False, False, 0)

        # Mask creation HBox
        mask_hbox = gtk.HBox(spacing=2)
        
        # Create and add combo box that holds added labels to be added by the user as masks
        self.label_combo = gtk.combo_box_new_text()
        mask_hbox.pack_start(self.label_combo, True, True, 2)
        
        # value to keep track of the region being saved, independent of label
        self.region_id = 1
        self.max_id = 1

        # Create and add SpinButton to hold the value of the region_id to be saved
        self.sb_adj = gtk.Adjustment(value=1, lower=1, upper=1)
        self.instance_id_btn = gtk.SpinButton(climb_rate=1.0, digits=0, adjustment=self.sb_adj)
        mask_hbox.pack_start(self.instance_id_btn, False, False, 2)

        # Add mask_hbox to the main_vbox
        main_vbox.pack_start(mask_hbox, False, False, 2)

        # Create and add 'Save selected mask' label
        add_mask_btn = gtk.Button('Save selected mask')
        add_mask_btn.connect("clicked", self.save_mask_on_click)
        main_vbox.pack_start(add_mask_btn, False, False, 2)

        # Dict to keep track of the amount of regions (consequently, number of IDs) present
        self.region_db = dict()

        # Dict to keep track of vector paths of each selection used, NOT TO BE USED VIA GIMP
        # saved so that they may be used by a neural network later
        self.path_db = dict()

        # Create list to be displayed to the user of saved masks

        # Object storing text values to be display to the user
        self.mask_store = gtk.ListStore(gobject.TYPE_STRING)

        # Gtk widget that displays ListStore to user
        self.mask_view = gtk.TreeView(model=self.mask_store)

        # Default renderer for displaying text
        renderer = gtk.CellRendererText()

        # Only one column needs to be displayed, only one added
        self.masks_col = gtk.TreeViewColumn('Masks', renderer, text=0)
        
        self.mask_view.append_column(self.masks_col)

        self.mask_view.set_size_request(-1, 200)
        main_vbox.pack_start(self.mask_view, True, True, 2)

        # Create and add 'Export Files & Quit' button
        export_btn = gtk.Button('Export files & quit')

        # Connect export_on_click function to the export_btn button
        export_btn.connect("clicked", self.export_on_click)
        main_vbox.pack_start(export_btn, False, False, 2)

        # Render all widgets to be displayed to the user
        self.show_all()


        # Save the original antialiasing settings to be restored when program is quit
        # 1/0 masks are required and AA creates blending effect - NOT WANTED
        self.orig_aa_setting = pdb.gimp_context_get_antialias()

        # Force AA settings to false
        pdb.gimp_context_set_antialias(False)


        # Retrieve the filename of the current loaded image - crashes if temp is loaded
        self.filename = pdb.gimp_image_get_filename(self.img)

        # Retrieve the directory of where the image is saved
        self.dir = os.path.split(self.filename)

        # Save the image name
        self.img_name = os.path.splitext(self.dir[1])

        # Create path of where masks will be saved
        self.mask_dir = os.path.join(self.dir[0], 'masks/')

        # Create path of where annotations will be saved
        self.annot_dir = os.path.join(self.dir[0], 'annotations/')



        self.selection_area_setup()
        pdb.gimp_displays_flush()

        return win

    """
    Adds text within the add_label_entry and places it as an option in the 
    label selector
    """
    def add_label_on_click(self, widget):
        # Retrieve the text from the add_label_entry
        label = self.add_label_entry.get_text()

        # Add the retrieved text to an option in the ComboBox
        self.label_combo.append_text(label)

        # Clear the text in the add_label_entry
        self.add_label_entry.set_text('')

    """
    Creates and initalises the layer where the segmentation mask will be stored
    """
    def selection_area_setup(self):
        NAME = 'Instance Segmentation Mask'
        
        # Retrieve the height and width of the parent image
        self.height = pdb.gimp_image_height(self.img)
        self.width = pdb.gimp_image_width(self.img)

        # Create the new layer with the aforementioned height and width
        # 0 = foregound fill, 28 = layer fill normal
        self.annot_layer = pdb.gimp_layer_new(self.img, self.width, self.height, 0, NAME, 100, 28)

        # Add the created layer to the image
        pdb.gimp_image_insert_layer(self.img, self.annot_layer, None, 1)
        
        # Fill the image with white (255,255,255) to denote background
        pdb.gimp_drawable_fill(self.annot_layer, 2)
        pdb.gimp_message('Setup Complete.')


    """
    Retrieves the current selected region within the GIMP image, transfers the selection
    to the annotation layer and fills with the selected colour (region id)
    """
    def save_mask_on_click(self, widget):
        # Make sure a selection exists, if not return with error message
        if pdb.gimp_selection_is_empty(self.img):
            pdb.gimp_message('No selection - Select an area first')
            return

        # Make sure a label selection exists, if not return with error message
        if self.label_combo.get_active_text() is None:
            pdb.gimp_message('No label selected - add and select a label first')
            return

        # Retrieve the region_id from the SpinButton
        self.region_id = int(self.sb_adj.get_value())

        # Using the region_id, create a color for GIMP to use
        rgb = id2rgb(self.region_id)

        # Set the color (foreground color) to the created region_id color
        pdb.gimp_context_set_foreground(rgb)

        # Fill the selected area with that color
        pdb.gimp_drawable_edit_fill(self.annot_layer, 0)

        # Convert selection to a path, this is an imperfect process using vectors
        # (DO NOT recreate selection from path if selection is needed, instead store 
        # selection as channel elsewhere)
        path = pdb.plug_in_sel2path(self.img, None)

        # Store path as string to be saved as text with annotation file
        self.path_db[self.region_id] = pdb.gimp_vectors_export_to_string(self.img, path)

        # Reset selection
        pdb.gimp_selection_none(self.img)

        # Get active text in label_combo as the selected label
        label = self.label_combo.get_active_text()

        # Store selected label in the region_db dict
        self.region_db[self.region_id] = label

        # Create the string to be displayed in the TreeView
        text = '(' + str(self.region_id) + ') ' + str(label)

        # Add the text in the model for the TreeView to be displayed to the user
        self.mask_store.append([text])
        
        # Add 1 to the region id (i.e. move onto the next region)
        self.region_id += 1

        # Set new restrictions for selecting region id
        # If the region_id exceeds the max that exists (i.e. brand new region)
        # then update the max and set that max in the SpinButton
        if self.region_id > self.max_id:
            self.max_id = self.region_id
            self.sb_adj.set_upper(self.max_id)
        
        self.sb_adj.set_value(self.max_id)

    """
    Saves the annotation layer as it's own image in the masks folder, along with saving the 
    region information as a JSON file in the previously made annotations fodler, then quits
    the program (a new instance of the program currently must exist for each image)
    """
    def export_on_click(self, widget):
        pdb.gimp_message('Exporting...')
        # If the mask/annot directory doesn't exist, make it
        try:
            os.makedirs(self.mask_dir)
            os.makedirs(self.annot_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Create the mask image name (original image name without the extention with the '_mask' in title)
        mask_filename = str(self.img_name[0]).replace(' ', '_') + '_mask.png'

        # Create path of where mask will be saved (for GIMP)
        mask_path = os.path.join(self.mask_dir, mask_filename)

        # Attempt saving of the annotation layer, if any error is raised, displayed to the user
        try:
            pdb.gimp_message('Attempting save of ' + str(self.annot_layer) + 'AKA (' + str(mask_filename) +  ') to ' + str(mask_path))
            pdb.file_png_save(None,                 # Input image
                              self.annot_layer,     # Drawable to save
                              mask_path,            # Path to save the image to
                              mask_filename,        # Name of the saved image
                              False,                # Interlacing?
                              0,                    # Compression?
                              True,                 # bKGD?
                              True,                 # gAMA?
                              True,                 # oFFs?
                              True,                 # pHYs?
                              True)                 # tIME?
            pdb.gimp_message('layer saved')
        except Exception as e:
            pdb.gimp_message(e)

        # Create the annotation file in the JSON format
        # Create the annotation filename (original image filename -extention + '_annotations')
        annot_filename = str(self.img_name[0]).replace(' ', '_') + '_annotations.json'

        # Path where annotations will be saved
        annot_path = os.path.join(self.annot_dir, annot_filename)

        # Create dictionary representing top-level JSON file
        json_top = {'image' : self.dir[1],
                    'mask' : 'masks/' + mask_filename,
                    'regions' : self.region_db,
                    'paths' : self.path_db
                    }
        
        pdb.gimp_message('Annotations file created')

        # Save JSON Dict
        with open(annot_path, 'w') as f:
            json.dump(json_top, f, indent=4)
        self.reset_and_quit()

    """
    Resets original AA settings and quits application
    """
    def reset_and_quit(self):
        pdb.gimp_context_set_antialias(self.orig_aa_setting)
        gtk.main_quit()

"""
Takes a given region id and creates an RGB value to be used in the annotation layer
:param val: region id to be turned into rgb value
:returns: rgb value as a gimpcolor object
"""
def id2rgb(val):
    return gimpcolor.RGB(int(val), int(val), int(val))

"""
Main function to run and load GUI
"""
def image_annotator(image, layer):
    window = IAWindow(image, layer)
    gtk.main()

"""
Tuple that holds information for GIMP to know what to do with the plug-in
"""
register(
    "python_fu_image_annotator",
    "Instance segmentaion labelling",
    "Instance segmentaion labelling",
    "Kieran Atkins",
    "Kieran Atkins",
    "2021",
    "<Image>/Toolbox/Image Annotator",
    "*",      # * = Works with existing image only
    [],
    [],
    image_annotator)

main()
