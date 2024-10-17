#!/usr/bin/env python

# from gimpfu import *
from gimpfu import pdb, register, main
import gtk
import gobject
import gimpcolor
import os
import json
import errno


class IAWindow(gtk.Window):

    # init the GUI
    def __init__(self, img, layer, *args, **kwargs):
        super(IAWindow, self).__init__(*args, **kwargs)
        self.NAME = 'Image Annotator'
        self.running = False

        # Stores the current img id (GIMP's)
        self.img = img
        self.width = pdb.gimp_image_width(self.img)
        self.height = pdb.gimp_image_height(self.img)

        # Force AA settings to false
        pdb.gimp_context_set_antialias(False)

        # Retrieve image filename and directory, then save image and create paths
        # for masks and annotatons
        self.filename = pdb.gimp_image_get_filename(self.img)
        if self.filename is None:
            pdb.gimp_message('Image must be saved in location before opening GIA')
            return

        # Setup paths for storing data
        repopulate = False
        self.root, self.filename = os.path.split(self.filename)  # get parent
        self.filename, self.filename_ext = os.path.splitext(self.filename)  # Gets name without extension
        self.annot_dir = os.path.join(self.root, self.filename + '_annotations')
        self.annot_file = os.path.join(self.annot_dir, self.filename + '_annotations.json')
        self.image_layer = pdb.gimp_image_get_active_layer(self.img)

        # Data stores
        self.annots = []  # List[Dict]
        self.store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.curr_id = 0

        self.setup_gui(*args)

        # Test if directory already exists, if does, repopulate with existing data
        try:
            os.makedirs(self.annot_dir)
            open(self.annot_file, 'w').close()  # initialise annotation file
        except OSError as e:
            if e.errno == 17:  # already exists
                pdb.gimp_message('Found existing files. Loading...')
                self.repopulate()
            else:
                raise e

        self.show_all()

        pdb.gimp_displays_flush()
        return

    def repopulate(self):
        file_size = os.stat(self.annot_file).st_size
        if file_size > 0:
            with open(self.annot_file, mode='r') as f:
                a = json.load(f)
                labels = set()
                if len(a) > 0:
                    # Add existing objects to list
                    for v in a:
                        labels.add(v['label'])
                        self.curr_id = max(v['id'], self.curr_id)
                        self.store.append([v['label'], v['id']])
                        self.annots.append({'id': int(v['id']),
                                            'filename': str(v['filename']),
                                            'label': str(v['label'])})
                    self.curr_id += 1
                    # Add existing labels
                    for label in labels:
                        self.label_combo.append_text(label)
        else:
            pdb.gimp_message('Existing file is empty')
            a = []

    def setup_gui(self, *args):
        gtk.Window.__init__(self, *args)
        self.set_title(self.NAME)
        self.set_border_width(10)

        # Obey the window manager quit signal:
        self.connect("destroy", gtk.main_quit)

        # The main layout, holds all other layouts
        vbox_main = gtk.VBox(spacing=8)

        # Add the main layout to the Window (self)
        self.add(vbox_main)

        # Add ID stating which image the toolbox is operating on and a seperator
        img_id_label = gtk.Label(self.filename + self.filename_ext)
        img_id_label.set_justify(gtk.JUSTIFY_LEFT)
        vbox_main.pack_start(img_id_label, False, False, 0)
        hseperator_0 = gtk.HSeparator()
        vbox_main.pack_start(hseperator_0, False, False, 2)

        # Create and add label denoting label creation section
        new_label_label = gtk.Label('Label creation')
        new_label_label.set_justify(gtk.JUSTIFY_LEFT)
        vbox_main.pack_start(new_label_label, False, False, 0)

        # Create and add text entry box for labels
        self.add_label_entry = gtk.Entry()
        vbox_main.pack_start(self.add_label_entry, False, False, 2)

        # Create, add and connect 'add label button'
        add_label_val_btn = gtk.Button('Add label value')
        add_label_val_btn.connect("clicked", self.add_label_on_click)
        vbox_main.pack_start(add_label_val_btn, False, False, 2)

        # Add section seperator (no functionality, only aesthetics)
        hseperator_1 = gtk.HSeparator()
        vbox_main.pack_start(hseperator_1, False, False, 2)

        # Create and add 'Mask creation' label
        add_label_label = gtk.Label('Mask creation')
        add_label_label.set_justify(gtk.JUSTIFY_LEFT)
        vbox_main.pack_start(add_label_label, False, False, 0)

        # Create and add combo box that holds added labels to be added by the user as masks
        self.label_combo = gtk.combo_box_new_text()
        vbox_main.pack_start(self.label_combo, False, False, 2)

        # Create and add 'Save selected mask' label
        add_mask_btn = gtk.Button('Save selected mask')
        add_mask_btn.connect("clicked", self.save_mask_on_click)
        vbox_main.pack_start(add_mask_btn, False, False, 2)

        # Gtk widget that displays ListStore to user
        self.mask_view = gtk.TreeView(model=self.store)
        self.mask_view.connect('size-allocate', self.treeview_changed)

        # Default renderer for displaying text
        renderer = gtk.CellRendererText()

        # Displays 'ID' and 'Masks' columns
        self.id_col = gtk.TreeViewColumn('ID ', renderer, text=1)
        self.mask_view.append_column(self.id_col)

        self.masks_col = gtk.TreeViewColumn('Label', renderer, text=0)
        self.mask_view.append_column(self.masks_col)

        # Adds ScrolledWindow for displaying TreeView
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        sw.add(self.mask_view)

        self.mask_view.set_size_request(-1, 200)
        vbox_main.pack_start(sw, True, True, 2)

        # Create and add 'Delete selected mask' button
        del_btn = gtk.Button('Delete selected mask')
        del_btn.connect('clicked', self.del_btn_on_click)
        vbox_main.pack_start(del_btn, False, False, 2)


    """
    Auto-scrolls TreeView to last entry when added
    """

    def treeview_changed(self, widget, event, data=None):
        adj = widget.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    """
    Deletes selected row from the widget, database and annotation layer
    """

    def del_btn_on_click(self, widget):

        # Gets currently selected row model and iter
        selection = self.mask_view.get_selection()
        model, tree_iter = selection.get_selected()

        # Gets selected row index and its 'ID' value
        index = selection.get_selected_rows()[1][0][0]
        label, idx = model[tree_iter]

        # Deletes the mask from the annots object and store object
        if index is not None:
            del_a = [a for a in self.annots if a['id'] == int(idx)][0]
            self.annots = [a for a in self.annots if a['id'] != int(idx)]
            del self.store[index]

            os.remove(os.path.join(self.annot_dir, del_a['filename']))
            with open(self.annot_file, 'w') as f:
                json.dump(self.annots, f, indent=4)
            pdb.gimp_message('Deleted ' + idx + ' (' + label + ') - ' + del_a['filename'])
        else:
            pdb.gimp_message('Unable to be find selected row')

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

        mask_layer = pdb.gimp_layer_new(self.img, self.width, self.height, 0, self.NAME, 100, 28)  #last param seems temperamental
        pdb.gimp_image_insert_layer(self.img, mask_layer, None, 1)

        # Set the color (foreground color) to the created region_id color
        pdb.gimp_context_set_foreground(gimpcolor.RGB(255, 255, 255))

        # Fill the selected area with that color
        pdb.gimp_drawable_edit_fill(mask_layer, 0)

        # Reset selection
        pdb.gimp_selection_none(self.img)

        # Get active text in label_combo as the selected label
        label = self.label_combo.get_active_text()

        pdb.file_png_save_defaults(self.img,  # Input image
                                   mask_layer,  # Drawable to save
                                   os.path.join(self.annot_dir, self.filename + '_' + str(self.curr_id) + '.png'),  # Path to save the image to
                                   self.filename + '_' + str(self.curr_id) + '.png',  # Name of the saved image
                                   )

        # Create the string to be displayed in the TreeView
        self.store.append([label, self.curr_id])
        self.annots.append({'id': int(self.curr_id),
                            'filename': self.filename + '_' + str(self.curr_id) + '.png',
                            'label': label})

        with open(self.annot_file, 'w') as f:
            json.dump(self.annots, f, indent=4)

        pdb.gimp_message('Annotation saved')
        self.curr_id += 1

        pdb.gimp_image_remove_layer(self.img, mask_layer)


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
    "Instance segmentation labelling",
    "Instance segmentation labelling",
    "Kieran Atkins",
    "Kieran Atkins",
    "2021",
    "<Image>/Toolbox/GIA 2",
    "*",  # * = Works with existing image only
    [],
    [],
    image_annotator)

main()
