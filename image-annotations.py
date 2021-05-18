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
        NAME = 'Image Annotations'

        self.running = False
        self.img = img
        self.annot_layer = layer
        win = gtk.Window.__init__(self, *args)
        self.set_title(NAME)
        self.set_border_width(10)

        # Obey the window manager quit signal:
        self.connect("destroy", self.reset_and_quit)

        vbox = gtk.VBox(spacing=8)
        self.add(vbox)

        new_label_label = gtk.Label('Label creation')
        new_label_label.set_justify(gtk.JUSTIFY_LEFT)
        vbox.pack_start(new_label_label, False, False, 0)

        self.add_label_entry = gtk.Entry()
        vbox.pack_start(self.add_label_entry, False, False, 2)

        add_label_val_btn = gtk.Button('Add label value')
        add_label_val_btn.connect("clicked", self.add_label_on_click)
        vbox.pack_start(add_label_val_btn, False, False, 2)

        hseperator_1 = gtk.HSeparator()
        vbox.pack_start(hseperator_1, False, False, 2)

        add_label_label = gtk.Label('Mask creation')
        add_label_label.set_justify(gtk.JUSTIFY_LEFT)
        vbox.pack_start(add_label_label, False, False, 0)

        hbox = gtk.HBox(spacing=2)

        self.label_combo = gtk.combo_box_new_text()
        hbox.pack_start(self.label_combo, True, True, 2)
        
        # value to keep track of the region being saved, independent of label
        self.region_id = 1
        self.max_id = 1

        self.sb_adj = gtk.Adjustment(value=1, lower=1, upper=1)
        self.instance_id_btn = gtk.SpinButton(climb_rate=1.0, digits=0, adjustment=self.sb_adj)
        hbox.pack_start(self.instance_id_btn, False, False, 2)

        vbox.pack_start(hbox, False, False, 2)

        add_mask_btn = gtk.Button('Save selected mask')
        add_mask_btn.connect("clicked", self.save_mask_on_click)
        vbox.pack_start(add_mask_btn, False, False, 2)

        # Dict to keep track of the amount of regions (consequently, number of IDs) present
        self.region_db = dict()
        self.path_db = dict()

        self.mask_store = gtk.ListStore(gobject.TYPE_STRING)
        self.mask_view = gtk.TreeView(model=self.mask_store)
        renderer = gtk.CellRendererText()
        self.masks_col = gtk.TreeViewColumn('Masks', renderer, text=0)
        self.mask_view.append_column(self.masks_col)

        self.mask_view.set_size_request(-1, 200)
        vbox.pack_start(self.mask_view, True, True, 2)

        export_btn = gtk.Button('Export files & quit')
        export_btn.connect("clicked", self.export_on_click)
        vbox.pack_start(export_btn, False, False, 2)

        self.show_all()

        self.orig_aa_setting = pdb.gimp_context_get_antialias()
        pdb.gimp_context_set_antialias(False)

        self.filename = pdb.gimp_image_get_filename(self.img)
        self.dir = os.path.split(self.filename)
        self.img_name = os.path.splitext(self.dir[1])
        self.mask_dir = os.path.join(self.dir[0], 'masks/')
        self.annot_dir = os.path.join(self.dir[0], 'annotations/')

        self.selection_area_setup()
        pdb.gimp_displays_flush()

        return win

    def add_label_on_click(self, widget):
        label = self.add_label_entry.get_text()
        self.label_combo.append_text(label)

        self.add_label_entry.set_text('')

    def selection_area_setup(self):
        NAME = 'Instance Segmentation Mask'
        self.height = pdb.gimp_image_height(self.img)
        self.width = pdb.gimp_image_width(self.img)
        # 0 = foregound fill, 28 = layer fill normal
        self.annot_layer = pdb.gimp_layer_new(self.img, self.width, self.height, 0, NAME, 100, 28)
        pdb.gimp_image_insert_layer(self.img, self.annot_layer, None, 1)
        pdb.gimp_drawable_fill(self.annot_layer, 2)
        pdb.gimp_message('Setup Complete.')


    def save_mask_on_click(self, widget): 
        pdb.gimp_image_undo_group_start(self.img) #undo needs to be fixed

        # make sure a selection exists
        if pdb.gimp_selection_is_empty(self.img):
            pdb.gimp_message('No selection - Select an area first')
            return

        if self.label_combo.get_active_text() is None:
            pdb.gimp_message('No label selected - add and select a label first')
            return

        # set colour (use hex)
        self.region_id = int(self.sb_adj.get_value())
        rgb = id2rgb(self.region_id)

        pdb.gimp_context_set_foreground(rgb)
        pdb.gimp_drawable_edit_fill(self.annot_layer, 0)

        path = pdb.plug_in_sel2path(self.img, None)
        self.path_db[self.region_id] = pdb.gimp_vectors_export_to_string(self.img, path)

        pdb.gimp_selection_none(self.img)

        label = self.label_combo.get_active_text()
        self.region_db[self.region_id] = label

        text = '(' + str(self.region_id) + ') ' + str(label)
        self.mask_store.append([text])

        self.region_id += 1
        if self.region_id > self.max_id:
            self.max_id = self.region_id
            self.sb_adj.set_upper(self.max_id)
        
        self.sb_adj.set_value(self.max_id)

        pdb.gimp_image_undo_group_end(self.img)

    def export_on_click(self, widget):
        pdb.gimp_message('export pressed')
        # if the mask/annot directory doesn't exist, make it
        pdb.gimp_message(self.mask_dir)
        pdb.gimp_message(self.annot_dir)
        try:
            os.makedirs(self.mask_dir)
            os.makedirs(self.annot_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # image export
        mask_filename = str(self.img_name[0]).replace(' ', '_') + '_mask.png'
        mask_path = os.path.join(self.mask_dir, mask_filename)

        try:
            pdb.gimp_message('attempting save of ' + str(self.annot_layer) + 'AKA (' + str(mask_filename) +  ') to ' + str(mask_path))
            pdb.file_png_save(None,
                              self.annot_layer,
                              mask_path,
                              mask_filename,
                              False,
                              0,
                              True,
                              True,
                              True,
                              True,
                              True)
            pdb.gimp_message('layer saved')
        except Exception as e:
            pdb.gimp_message(e)

        # json export
        annot_filename = str(self.img_name[0]).replace(' ', '_') + '_annotations.json'
        annot_path = os.path.join(self.annot_dir, annot_filename)

        json_top = {'image' : self.dir[1],
                    'mask' : 'masks/' + mask_filename,
                    'regions' : self.region_db,
                    'paths' : self.path_db
                    }
        
        pdb.gimp_message('json created')

        with open(annot_path, 'w') as f:
            json.dump(json_top, f, indent=4)

        self.reset_and_quit()

    def reset_and_quit(self):
        pdb.gimp_context_set_antialias(self.orig_aa_setting)
        gtk.main_quit()


def id2rgb(val):
    return gimpcolor.RGB(int(val), int(val), int(val))

def image_annotations_3(image, layer):
    window = IAWindow(image, layer)
    gtk.main()
    
register(
    "python_fu_image_annotations_3",
    "Instance segmentaion labelling",
    "Instance segmentaion labelling",
    "Kieran Atkins",
    "Kieran Atkins",
    "2021",
    "<Image>/Toolbox/Image Annotations",
    "*",      # Works with existing image only
    [],
    [],
    image_annotations_3)

main()
