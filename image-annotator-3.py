#!/usr/bin/env python

import os
import json

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import GObject, Gtk, Gio, Gegl
import sys

plug_in_proc = 'image-annotator'
plug_in_binary = 'py3-image-annotator'

# Helper function to streamline calling PDB functions
def run_procedure(_name:str, **kwargs):
    procedure = Gimp.get_pdb().lookup_procedure(_name)
    config = procedure.create_config()
    for key, val in kwargs.items():
        key = key.replace('_', '-')
        config.set_property(key, val)
    return procedure.run(config)

# ComboBoxText class, allowing for initalised placeholder text
class ComboBoxTextWithPlaceholder(Gtk.ComboBoxText):
    def __init__(self, placeholder=""):
        super().__init__(has_entry=True)
        self._placeholder = placeholder
        self._entry = self.get_child()
        self._entry.set_editable(False) 

        self._entry.set_property("can-focus", False)
        self._entry.set_text(self._placeholder)

class IAWindow(Gtk.Window):

    # init the GUI
    def __init__(self, img, drawables, *args, **kwargs):
        super(IAWindow, self).__init__(*args, **kwargs)
        self.NAME = 'Image Annotator'
        self.running = False

        # Stores the current img id (GIMP's)
        self.img = img
        self.width = run_procedure('gimp-image-get-width', image=self.img).index(1)
        self.height = run_procedure('gimp-image-get-height', image=self.img).index(1)

        # Force AA settings to false
        run_procedure('gimp-context-set-antialias', antialias=False)

        # Retrieve image filename and directory, then save image and create paths
        # for masks and annotatons
        self.filename = run_procedure('gimp-image-get-file', image=self.img).index(1).get_path()
        if self.filename is None:
            run_procedure('gimp-message', message='Image must be saved in location before opening GIA')
            return

        # Setup paths for storing data
        self.root, self.filename = os.path.split(self.filename)  # get parent
        self.filename, self.filename_ext = os.path.splitext(self.filename)  # Gets name without extension
        self.annot_dir = os.path.join(self.root, self.filename + '_annotations')
        self.annot_file = os.path.join(self.annot_dir, self.filename + '_annotations.json')

        # Data stores
        self.annots = []  # List[Dict]
        self.store = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.curr_id = 0

        self.setup_gui_v2(*args)

        # Test if directory already exists, if does, repopulate with existing data
        if os.path.isdir(self.annot_dir) and os.path.isfile(self.annot_file):
            run_procedure('gimp-message', message='Found existing files. Loading...')
            self.repopulate()
        else:
            os.makedirs(self.annot_dir, exist_ok=True)
            open(self.annot_file, 'w').close()

        self.show_all()

        run_procedure('gimp-displays-flush')
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
                        self.store.append([str(v['label']), str(v['id'])])
                        self.annots.append({'id': int(v['id']),
                                            'filename': str(v['filename']),
                                            'label': str(v['label'])})
                    self.curr_id += 1
                    # Add existing labels
                    for label in labels:
                        self.label_combo.append_text(label)
        else:
            run_procedure('gimp-message', message='Existing file is empty')
            a = []

    # Creates the GUI (v2)
    def setup_gui_v2(self, *args):
        Gtk.Window.__init__(self, *args)
        self.set_title(self.NAME)
        self.set_border_width(10)

        # Obey the window manager quit signal:
        self.connect("destroy", Gtk.main_quit)

        # The main layout, holds all other layouts
        vbox_main = Gtk.VBox(spacing=8)

        # Add the main layout to the Window (self)
        self.add(vbox_main)

        # Add ID stating which image the toolbox is operating on and a seperator
        img_id_label = Gtk.Label(label=self.filename + self.filename_ext)
        vbox_main.pack_start(img_id_label, False, False, 0)
        hseperator_0 = Gtk.HSeparator()
        vbox_main.pack_start(hseperator_0, False, False, 2)

        # HBox for class ComboBox and new label
        label_layout = Gtk.HBox(spacing=1, homogeneous=False)

        # Create and add combo box that holds added labels to be added by the user as masks
        self.placeholder_text = 'Select a label...'
        self.label_combo = ComboBoxTextWithPlaceholder(self.placeholder_text)
        label_layout.pack_start(self.label_combo, True, True, 2)

        # Button for adding new label
        add_label_val_btn = Gtk.Button(label='+')
        add_label_val_btn.connect("clicked", self.add_label_on_click)
        label_layout.pack_start(add_label_val_btn, False, False, 2)

        vbox_main.pack_start(label_layout, False, False, 2)

        # Create and add 'Save selected mask' label
        add_mask_btn = Gtk.Button(label='Save mask')
        add_mask_btn.connect("clicked", self.save_mask_on_click)
        vbox_main.pack_start(add_mask_btn, False, False, 2)

        hseperator_1 = Gtk.HSeparator()
        vbox_main.pack_start(hseperator_1, False, False, 2)

        # Gtk widget that displays ListStore to user
        self.mask_view = Gtk.TreeView(model=self.store)
        self.mask_view.connect('size-allocate', self.treeview_changed)

        # Default renderer for displaying text
        renderer = Gtk.CellRendererText()

        # Displays 'ID' and 'Masks' columns
        self.id_col = Gtk.TreeViewColumn('ID ', renderer, text=1)
        self.mask_view.append_column(self.id_col)

        self.masks_col = Gtk.TreeViewColumn('Label', renderer, text=0)
        self.mask_view.append_column(self.masks_col)

        # Adds ScrolledWindow for displaying TreeView
        sw = Gtk.ScrolledWindow()
        # sw.set_policy(Gtk.GTK_POLICY_NEVER, Gtk.GTK_POLICY_ALWAYS)
        sw.set_policy(2, 0)
        sw.add(self.mask_view)

        self.mask_view.set_size_request(-1, 200)
        vbox_main.pack_start(sw, True, True, 2)

        # Create and add 'Delete selected mask' button
        del_btn = Gtk.Button(label='Delete mask')
        del_btn.connect('clicked', self.del_btn_on_click)
        vbox_main.pack_start(del_btn, False, False, 2)

    # Auto-scrolls TreeView to last entry when added
    def treeview_changed(self, widget, event, data=None):
        adj = widget.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    # Deletes selected row from the widget, database and annotation layer
    def del_btn_on_click(self, widget):
        try:
            dialog = Gtk.Dialog(
                title="Delete mask?",
                parent=self,
                modal=True,
                destroy_with_parent=True
            )
            
            # Add standard buttons
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Delete", Gtk.ResponseType.OK)

            # Give buttons more spacing
            action_area = dialog.get_action_area()
            action_area.set_spacing(2)
            action_area.set_margin_top(10)
            action_area.set_margin_bottom(10)
            action_area.set_margin_left(10)
            action_area.set_margin_right(10)


            response = dialog.run()
            if response == Gtk.ResponseType.OK:
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
                    path = os.path.join(self.annot_dir, del_a['filename'])
                    if os.path.exists(path):
                        os.remove(os.path.join(self.annot_dir, del_a['filename']))
                        with open(self.annot_file, 'w') as f:
                            json.dump(self.annots, f, indent=4)
                        run_procedure('gimp-message', message='Deleted ' + idx + ' (' + label + ') - ' + del_a['filename'])
                    else:
                        run_procedure('gimp-message', message='Unable to find ' + idx + ' (' + label + ') - ' + del_a['filename'])

                else:
                    run_procedure('gimp-message', message='Unable to be find selected row')
        except IndexError:
            run_procedure('gimp-message', message='No row selected')
        finally:
            dialog.destroy()

    # Adds text within the add_label_entry and places it as an option in the label selector
    def add_label_on_click(self, widget):
        # Retrieve the text from dialog box
        dialog = Gtk.Dialog(
            title="Create New Label",
            parent=self,
            modal=True,
            destroy_with_parent=True
        )
        
        # Add standard buttons
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK", Gtk.ResponseType.OK)


        # Give buttons more spacing
        action_area = dialog.get_action_area()
        action_area.set_spacing(2)
        action_area.set_margin_top(10)

        # Create entry for label name
        entry = Gtk.Entry()
        entry.set_placeholder_text("Enter label name")

        # Sets dialog box to have focus on default
        entry.connect("activate", lambda e: dialog.response(Gtk.ResponseType.OK))
        dialog.set_default(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        
        # Add entry to dialog's content area
        content_area = dialog.get_content_area()
        content_area.add(entry)

        # Setup spacing in content area
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        
        content_area.show_all()
        entry.grab_focus()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            label = entry.get_text()
            if label:
                # Add the retrieved text to an option in the ComboBox
                self.label_combo.append_text(label)
                self.label_combo.set_active_id(label)

        dialog.destroy()

    # Retrieves the current selected region within the GIMP image, transfers the selection
    # to the annotation layer and fills with the selected colour (region id)
    def save_mask_on_click(self, widget):
        # Make sure a selection exists, if not return with error message
        if run_procedure('gimp-selection-is-empty', image=self.img):
            run_procedure('gimp-message', message='No selection - select an area first')
            return

        # Make sure a label selection exists, if not return with error message
        if self.label_combo.get_active_text() is None or self.label_combo.get_active_text() == self.placeholder_text:
            run_procedure('gimp-message', message='No label selected - add and select a label first')
            return
        
        annotation_image = run_procedure('gimp-image-new', width=self.width, height=self.height, type=0).index(1)
        annotation_layer = run_procedure('gimp-layer-new', image=self.img, name=self.NAME, width=self.width, height=self.height, type=0, opacity=100, mode=28).index(1)
        run_procedure('gimp-image-insert-layer', image=self.img, layer=annotation_layer, parent=None, position=1)

        # Set the color (foreground color) to the created region_id color
        color = Gegl.Color.new('#FFFFFF')
        run_procedure('gimp-context-set-foreground', foreground=color)

        # Fill the selected area with that color
        run_procedure('gimp-drawable-edit-fill', drawable=annotation_layer, fill_type=0)

        # Reset selection
        run_procedure('gimp-selection-none', image=self.img)

        # Get active text in label_combo as the selected label
        label = self.label_combo.get_active_text()

        # copy mask layer to new image
        copied_layer = run_procedure('gimp-layer-new-from-drawable', drawable=annotation_layer, dest_image=annotation_image).index(1)
        run_procedure('gimp-image-insert-layer', image=annotation_image, layer=copied_layer, parent=None, position=0)

        # save new mask layer image
        path = os.path.join(self.annot_dir, self.filename + '_' + str(self.curr_id) + '.png')
        file = Gio.File.new_for_path(path)
        run_procedure('file-png-export', run_mode=1, options=None, image=annotation_image,  file=file)

        # Create the string to be displayed in the TreeView
        self.store.append([label, str(self.curr_id)])
        self.annots.append({'id': int(self.curr_id),
                            'filename': self.filename + '_' + str(self.curr_id) + '.png',
                            'label': label})

        with open(self.annot_file, 'w') as f:
            json.dump(self.annots, f, indent=4)

        run_procedure('gimp-image-delete', image=annotation_image)
        run_procedure('gimp-image-remove-layer', image=self.img, layer=annotation_layer)
        run_procedure('gimp-message', message='Annotation saved')
        self.curr_id += 1



# Main function to run and load GUI
def image_annotator(procedure, run_mode, image, drawables, config, data):
    window = IAWindow(image, drawables)
    Gtk.main()


class ImageAnnotator(Gimp.PlugIn):
    def do_query_procedures(self):
        return [plug_in_proc]
    
    def do_create_procedure(self, name):
        procedure = None
        if name == plug_in_proc:
            procedure = Gimp.ImageProcedure.new(self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                image_annotator, None)
            # procedure.set_sensitivity_mask (Gimp.ProcedureSensitivityMask.DRAWABLE |
                                            # Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
            procedure.set_menu_label("GIA3")
            procedure.set_attribution("Atkins", "Atkins, Kieran", "2025")
            procedure.add_menu_path ("<Image>/Annotation")
            procedure.set_documentation ("Image annotation plug-in to take GIMP's powerful selection toolbox to " +
                                         "create segmentation masks to train Deep Learning models", None)
        return procedure

Gimp.main(ImageAnnotator.__gtype__, sys.argv)