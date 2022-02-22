#-*- coding: utf-8 -*-

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info={
    "name" : "Transfer Shape Keys Via Deform",
    "description": "Transfer shape keys from active to selected via deform modifier",
    "author" : "konoha18537007",
    "version" : (1, 1),
    "blender": (3, 0, 0),
    "category": "Object",
    "location": "View3D > Object",
    #"wiki_url": "",
    #"tracker_url": "",
}

import bpy


# Abstract base class
# Child classes: 
#   TransferShapeKeysViaSurfaceDeform
#   TransferShapeKeysViaMeshDeform
class TransferShapeKeys(bpy.types.Operator):
    
    DEBUG = False
    
    def validate_selection(self, context, selected, active):
        if active is None:
            self.report({"ERROR"},"Please set an active object")
            return False
        if active.type != "MESH":
            self.report({"ERROR"},"Active object is not a mesh")
            return False
        if active.data.shape_keys is None:
            self.report({"ERROR"},"Active object has no shape keys")
            return False
        if len(selected) < 1:
            self.report({"ERROR"},"Please select more than 1 object (active = source, selected = target)")
            return False
        return True
    
    def store_shape_key_settings(self, context, obj):
        settings = {}
        try:
            key_blocks = obj.data.shape_keys.key_blocks
            
            for key_block in key_blocks:
                settings[key_block.name] = (key_block.value, key_block.mute)
        except:
            pass
        finally:
            return settings
         
    def restore_shape_key_settings(self, context, obj, settings):
        try:
            key_blocks = obj.data.shape_keys.key_blocks
            
            for key_name, tuple in settings.items():
                key_blocks[key_name].value = tuple[0]
                key_blocks[key_name].mute = tuple[1]
        except:
            pass

    def mute_all_shape_keys(self, context, obj):
        try:
            key_blocks = obj.data.shape_keys.key_blocks
            
            for key_block in key_blocks:
                key_block.mute = True      
        except:
            pass

    def unmute_all_shape_keys(self, context, obj):
        try:
            key_blocks = obj.data.shape_keys.key_blocks
            
            for key_block in key_blocks:
                key_block.mute = False      
        except:
            pass

    def zero_all_shape_keys(self, context, obj):
        try:
            key_blocks = obj.data.shape_keys.key_blocks
            
            for key_block in key_blocks:
                key_block.value = 0.0          
        except:
            pass
    
    def add_driver(self, context, shape_key, property, target_id, target_data_path):
        driver = shape_key.driver_add(property).driver
        driver.type = 'AVERAGE'
        var = driver.variables.new()
        var.targets[0].id_type = 'KEY'
        var.targets[0].id = target_id
        var.targets[0].data_path = target_data_path
    
    def add_sk_drivers(self, context, sk_map, src_shape_keys):
        for sk_tuple in sk_map:
            new_sk = sk_tuple[0]
            src_sk = sk_tuple[1]
            self.add_driver(context, new_sk, 'value', src_shape_keys, src_sk.path_from_id('value'))
            self.add_driver(context, new_sk, 'mute', src_shape_keys, src_sk.path_from_id('mute'))
            self.add_driver(context, new_sk, 'slider_min', src_shape_keys, src_sk.path_from_id('slider_min'))
            self.add_driver(context, new_sk, 'slider_max', src_shape_keys, src_sk.path_from_id('slider_max'))
      
    def remove_shapekey(self, context, obj, shapekey_name):
        try:
            obj.shape_key_remove(obj.data.shape_keys.key_blocks.get(shapekey_name))
        except:
            pass
        
    def save_as_shapekey(self, context, obj, key_block, mod_name):
        key_block.value = 1.0
        context.view_layer.objects.active = obj
        apply_ret = bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod_name, report=True)
        key_block.value = 0.0
        if 'FINISHED' not in apply_ret:
            s = 'Error on applying modifier, Object: {0}, ShapeKey: {1}, apply modifier: {2}'
            self.report({'ERROR'}, s.format(obj.name, key_block.name, apply_ret))
            return None
        else:
            new_shape_key = obj.data.shape_keys.key_blocks[-1]
            new_shape_key.name = key_block.name # rename
            return new_shape_key
    
    def debug(self,msg):
        if self.DEBUG:
            self.report({"INFO"},msg)
        return
    
    def get_objects(self, context, valid_tgt_types):
        obj_src = context.active_object
        obj_tgts = [x for x in context.selected_objects if x != obj_src and x.type in valid_tgt_types]
        return obj_src, obj_tgts


def vg_enum_callback(context):
    vg_enum_callback.items.clear()
    selected = context.selected_objects
    active = context.active_object
    
    vg_names = {}
    for obj in selected:
        if obj == active:
            continue
        try:
            for vg in obj.vertex_groups:
                if vg.name not in vg_names:
                    vg_names[vg.name] = []
                vg_names[vg.name].append(obj.name)
        except:
            pass
        
    empty_item = ('NONE','(None)','',)
    vg_enum_callback.items.append(empty_item)
    
    for vg_name,obj_list in vg_names.items():
        tooltip = "Found in:\n"
        tooltip += '\n'.join(obj_list)
        item = (
            vg_name + '_id',    # identifier
            vg_name,            # name
            tooltip,            # description
        )
        vg_enum_callback.items.append(item)
vg_enum_callback.items = []     # "There is a known bug with using a callback, Python must 
                                # keep a reference to the strings returned by the callback 
                                # or Blender will misbehave or even crash."
                                # https://docs.blender.org/api/current/bpy.props.html#bpy.props.EnumProperty
                                

class TransferShapeKeysViaSurfaceDeform(TransferShapeKeys):
    """Transfer Shape Keys Via Surface Deform"""
    bl_label = "Transfer Shape Keys Via Surface Deform"
    bl_idname = "object.transfer_shape_keys_via_surface_deform"
    bl_options = {'REGISTER', 'UNDO'}
    
    valid_tgt_types = ['MESH']
    
    use_existing_mod: bpy.props.BoolProperty(
        name="Use Existing Modifier",
        description="Try to find existing Surface Deform modifier on selected objects before creating a new (temporary) modifier.\nUseful for setting per-object deform falloff/strength/vertex group.\nExisting modifier does not need to be unmuted",
        default=True,
    )
    mute_existing_mod: bpy.props.BoolProperty(
        name="Mute Existing Mod After Transfer",
        description="Mute existing Surface Deform modifier after transfering shape keys (otherwise shape keys can't be viewed properly)",
        default=True,
    )
    move_to_first:  bpy.props.BoolProperty(
        name="Move to first",
        description="Move temporary deform modifier to the top of the modifier list. This is necessary when there are unapplied generative modifiers, as they break shape keys",
        default=True,
    )
    falloff: bpy.props.FloatProperty(
        name="Interpolation Falloff",
        description="Controls how much nearby polygons influence deformation",
        default=4.0,
        min=2.0,
        max=16.0,
    )
    strength: bpy.props.FloatProperty(
        name = "Strength",
        description = "Strength of modifier deformations",
        default = 1.0,
    )
    vg_name: bpy.props.EnumProperty(
        name = "Vertex Group (Optional)",
        description = "Vertex group name for selecting/weighting the affected area. \nWill attempt to find the same vertex group in all selected objects",
        items = lambda self, context: vg_enum_callback.items,
    )
    vg_invert: bpy.props.BoolProperty(
        name="",
        description="Invert\nInvert vertex group influence",
        default=False,
    )
    add_drivers: bpy.props.BoolProperty(
        name = "Add Drivers",
        description = "Add drivers for created shape keys (shape keys will be driven by source object)",
        default = True,
    )
    ignore_muted: bpy.props.BoolProperty(
        name = "Don't Copy Muted",
        description = "Muted shape keys in source object will not be copied",
        default = False,
    )
    suppress: bpy.props.BoolProperty(
        name = "Suppress Other Shape Keys",
        description = "Other shape keys on destination object will be suppressed so that they are not baked into copied shape keys",
        default = True,
    )
    overwrite: bpy.props.BoolProperty(
        name = "Overwrite Existing",
        description = "Existing shape keys will be overwritten",
        default = True,
    )
    
    def __find_existing_surface_deform_modifier(self, context, obj):
        mod = None
        for m in obj.modifiers:
            if m.type == 'SURFACE_DEFORM':
                if not m.is_bound:
                    self.report({"WARNING"},"Existing Surface Deform Modifier found in unbound state. Did you forget to bind it?")
                    continue
                mod = m
                break
        return mod

    def __add_and_bind_surface_deform_modifier(self, context, obj, target, move_to_first, falloff, strength, vg_name, vg_invert):
        def_mod = None
        try:
            context.view_layer.objects.active = obj
            
            def_mod = obj.modifiers.new(type='SURFACE_DEFORM', name="TEMP_SurfaceDeform")
            if move_to_first:
                bpy.ops.object.modifier_move_to_index(modifier=def_mod.name, index=0)
            def_mod.target = target
            def_mod.falloff = falloff
            def_mod.strength = strength
            if vg_name:
                def_mod.vertex_group = vg_name
            def_mod.invert_vertex_group = vg_invert
            
            bpy.ops.object.surfacedeform_bind(modifier = def_mod.name)
            context.view_layer.objects.active = target 
        except:
            pass
        finally:
            return def_mod
        
    def __get_surface_def_mod(self, context, use_existing_mod, obj, target, move_to_first, falloff, strength, vg_name, vg_invert):
        existing_mod_found = False
        def_mod = None
        if use_existing_mod:
            def_mod = self.__find_existing_surface_deform_modifier(context, obj)
            if def_mod is not None:
                existing_mod_found = True
        if def_mod is None:
            def_mod = self.__add_and_bind_surface_deform_modifier(context, obj, target, move_to_first, falloff, strength, vg_name, vg_invert)
        
        return def_mod, existing_mod_found
    
    
    def process(self, context, use_existing_mod, mute_existing_mod, move_to_first, falloff, strength, vg_name, vg_invert,
                add_drivers, ignore_muted, suppress, overwrite):
                    
        ret = True
        
        # get objects' references
        obj_src, obj_tgts = self.get_objects(context, self.valid_tgt_types)
        
        if not self.validate_selection(context, obj_tgts, obj_src):
            ret = False
            return ret
        
        self.debug("num shape keys : {0}".format(len(obj_src.data.shape_keys.key_blocks)))
        
        # memorize all shape keys' values and set them to 0
        stored_source_settings = self.store_shape_key_settings(context, obj_src)
        self.zero_all_shape_keys(context, obj_src)
        if not ignore_muted: self.unmute_all_shape_keys(context, obj_src)
        
        # loop over target objects
        for o in obj_tgts:
            stored_tgt_settings = self.store_shape_key_settings(context, o)
            if suppress: self.mute_all_shape_keys(context, o)
            def_mod, existing_mod_found = self.__get_surface_def_mod(context, use_existing_mod, o, obj_src, 
                                                                     move_to_first, falloff, strength, vg_name, vg_invert)

            self.debug("modifier name: {0}".format(def_mod.name))
            
            src_shape_keys = obj_src.data.shape_keys
            src_key_blocks = src_shape_keys.key_blocks
            
            sk_map = []
            for i,kb in enumerate(src_key_blocks):
                if i == 0: continue                     # Skip basis
                if ignore_muted and kb.mute: continue   # Skip muted
                if overwrite: self.remove_shapekey(context, o, kb.name)
                
                new_shape_key = self.save_as_shapekey(context, o, kb, def_mod.name)
                if new_shape_key is None:
                    ret = False
                else:
                    sk_map.append((new_shape_key, kb))
                    
            if add_drivers: self.add_sk_drivers(context, sk_map, src_shape_keys)
            if not existing_mod_found: o.modifiers.remove(def_mod)
            self.restore_shape_key_settings(context, o, stored_tgt_settings)
            if existing_mod_found and mute_existing_mod:
                def_mod.show_viewport = False
            
        context.view_layer.objects.active = obj_src 
        self.restore_shape_key_settings(context, obj_src, stored_source_settings)
        
        
        return ret
        
        
    def execute(self, context):
        vg_enum_callback(context)
        vg_n = None if self.vg_name == 'NONE' else self.vg_name[:-3]
        
        self.process(context, self.use_existing_mod, self.mute_existing_mod, 
                     self.move_to_first, self.falloff, self.strength, vg_n, self.vg_invert,
                     self.add_drivers, self.ignore_muted, self.suppress, self.overwrite)
        
        return {'FINISHED'}
    
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "use_existing_mod")
        ex_col = layout.column()
        ex_col.enabled = self.use_existing_mod
        ex_col.prop(self, "mute_existing_mod")

        layout.separator(factor=1)
        
        layout.label(text = "Fallback Surface Deform Settings")
        def_box = layout.box()
        def_box.prop(self, "move_to_first")
        def_box.prop(self, "falloff")
        def_box.prop(self, "strength")
        vg_row = def_box.row()
        vg_row.prop(self, "vg_name")
        vg_row.prop(self, "vg_invert", icon="ARROW_LEFTRIGHT")

        layout.label(text = "Shape Key Settings")
        sk_box = layout.box()
        sk_box.prop(self, "add_drivers")
        sk_box.prop(self, "ignore_muted")
        sk_box.prop(self, "suppress")
        sk_box.prop(self, "overwrite")


class TransferShapeKeysViaMeshDeform(TransferShapeKeys):
    """Transfer Shape Keys Via Mesh Deform"""
    bl_label = "Transfer Shape Keys Via Mesh Deform"
    bl_idname = "object.transfer_shape_keys_via_mesh_deform"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Objects of type Curve and Surface can have Shape Keys and Mesh Deform modifiers, but:
    # -the modifier can't be applied/saved as Shape Key so we can't copy Shape Keys to them
    # -they can't be set as the target for a Surface/Mesh Deform modifier, so we can't copy
    #  Shape Keys from them
#    valid_tgt_types = ['MESH', 'SURFACE', 'CURVE']
    valid_tgt_types = ['MESH']
    
    use_existing_mod: bpy.props.BoolProperty(
        name="Use Existing Mesh Deform Modifier",
        description="Try to find existing Mesh Deform modifier on selected objects before creating a new (temporary) modifier.\nUseful for setting per-object deform falloff/strength/vertex group.\nExisting modifier does not need to be unmuted",
        default=True,
    )
    mute_existing_mod: bpy.props.BoolProperty(
        name="Mute After Transfer",
        description="Mute existing Surface Deform modifier after transfering shape keys (otherwise shape keys can't be viewed properly).",
        default=True,
    )
    move_to_first:  bpy.props.BoolProperty(
        name="Move to first",
        description="Move temporary deform modifier to the top of the modifier list. This is necessary when there are unapplied generative modifiers, as they break shape keys",
        default=True,
    )
    precision: bpy.props.IntProperty(
        name = "Precision",
        description = "The grid size for binding",
        default = 4,
        options = {'SKIP_SAVE'},
        min = 2,
        max = 10,
    )
    vg_name: bpy.props.EnumProperty(
        name = "Vertex Group (Optional)",
        description = "Vertex group name for selecting/weighting the affected area. \nWill attempt to find the same vertex group in all selected objects",
        items = lambda self, context: vg_enum_callback.items,
    )
    vg_invert: bpy.props.BoolProperty(
        name="",
        description="Invert\nInvert vertex group influence",
        default=False,
    )
    add_drivers: bpy.props.BoolProperty(
        name = "Add Drivers",
        description = "Add drivers for created shape keys (shape keys will be driven by source object)",
        default = True,
    )
    ignore_muted: bpy.props.BoolProperty(
        name = "Don't Copy Muted",
        description = "Muted shape keys in source object will not be copied",
        default = False,
    )
    suppress: bpy.props.BoolProperty(
        name = "Suppress Other Shape Keys",
        description = "Other shape keys on destination object will be suppressed so that they are not baked into copied shape keys",
        default = True,
    )
    overwrite: bpy.props.BoolProperty(
        name = "Overwrite Existing",
        description = "Existing shape keys will be overwritten",
        default = True,
    )
    
    use_sld_mod: bpy.props.BoolProperty(
        name = "Add Simple Solidify Modifier",
        description = "Add a basic, temporary Solidify modifier on active object. The Mesh Deform modifier works best when the target object surrounds the deformed mesh. For more control, uncheck this option and manually add a Solidify modifier to the active object",
        default = False,
    )
    sld_thickness: bpy.props.FloatProperty(
        name = "Thickness",
        description = "Thickness of the shell",
        default = 0.5,
    )
    sld_offset: bpy.props.FloatProperty(
        name = "Offset",
        description = "Offset the thickness from the center",
        default = 0.0,
        min = -1.0,
        max = 1.0,
    )
    
    def __find_existing_solidify_modifier(self, context, obj):
        for m in obj.modifiers:
            if m.type == 'SOLIDIFY':
                return m
        
    def __add_solidify_modifier(self, context, obj, thickness, offset):
        solid_mod = None
        try:
            solid_mod = obj.modifiers.new(type='SOLIDIFY', name='TEMP_Solidify')
            solid_mod.thickness = thickness
            solid_mod.offset = offset
        except:
            pass
        finally:
            return solid_mod
        
    def __find_existing_mesh_deform_modifier(self, context, obj):
        mod = None
        for m in obj.modifiers:
            if m.type == 'MESH_DEFORM':
                if not m.is_bound:
                    self.report({"WARNING"},"Existing Mesh Deform Modifier found in unbound state. Did you forget to bind it?")
                    continue
                mod = m
                break
        return mod

    def __add_and_bind_mesh_deform_modifier(self, context, obj, target, move_to_first, precision, vg_name, vg_invert):
        def_mod = None
        try:
            context.view_layer.objects.active = obj
            
            def_mod = obj.modifiers.new(type='MESH_DEFORM', name='TEMP_MeshDeform')
            if move_to_first:
                bpy.ops.object.modifier_move_to_index(modifier=def_mod.name, index=0)
            def_mod.object = target
            def_mod.precision = precision
            if vg_name:
                def_mod.vertex_group = vg_name
            def_mod.invert_vertex_group = vg_invert
            
            bpy.ops.object.meshdeform_bind(modifier=def_mod.name)
            context.view_layer.objects.active = target 
        except:
            pass
        finally:
            return def_mod
        
    def __get_mesh_def_mod(self, context, use_existing_mod, obj, target, move_to_first, precision, vg_name, vg_invert):
        existing_mod_found = False
        def_mod = None
        if use_existing_mod:
            def_mod = self.__find_existing_mesh_deform_modifier(context, obj)
            if def_mod is not None:
                existing_mod_found = True
        if def_mod is None:
            def_mod = self.__add_and_bind_mesh_deform_modifier(context, obj, target, move_to_first, precision, vg_name, vg_invert)
        
        return def_mod, existing_mod_found
    
    
    def process(self, context, use_existing_mod, mute_existing_mod, move_to_first, precision, vg_name, vg_invert, 
                add_drivers, ignore_muted, suppress, overwrite, use_sld_mod, sld_thickness, sld_offset):
    
        ret = True
        
        # get objects' references
        obj_src, obj_tgts = self.get_objects(context, self.valid_tgt_types)
        
        if not self.validate_selection(context, obj_tgts, obj_src):
            ret = False
            return ret
        
        self.debug("num shape keys : {0}".format(len(obj_src.data.shape_keys.key_blocks)))
        
        # memorize all shape keys' values and set them to 0
        stored_source_settings = self.store_shape_key_settings(context, obj_src)
        sld_mod = None
        if use_sld_mod: sld_mod = self.__add_solidify_modifier(context, obj_src, sld_thickness, sld_offset)
        self.zero_all_shape_keys(context, obj_src)
        if not ignore_muted: self.unmute_all_shape_keys(context, obj_src)
        
        # loop over target objects
        for o in obj_tgts:
            stored_tgt_settings = self.store_shape_key_settings(context, o)
            if suppress: self.mute_all_shape_keys(context, o)
            def_mod, existing_mod_found = self.__get_mesh_def_mod(context, use_existing_mod, o, obj_src,
                                                                  move_to_first, precision, vg_name, vg_invert)
            
            if existing_mod_found and sld_mod: sld_mod.show_viewport = False
            self.debug("modifier name: {0}".format(def_mod.name))

            src_shape_keys = obj_src.data.shape_keys
            src_key_blocks = src_shape_keys.key_blocks
            
            sk_map = []
            for i,kb in enumerate(src_key_blocks):
                if i == 0: continue                     # Skip basis
                if ignore_muted and kb.mute: continue   # Skip muted
                if overwrite: self.remove_shapekey(context, o, kb.name)

                new_shape_key = self.save_as_shapekey(context, o, kb, def_mod.name)
                if new_shape_key is None:
                    ret = False
                else:
                    sk_map.append((new_shape_key, kb))
            
            if add_drivers: self.add_sk_drivers(context, sk_map, src_shape_keys)
            if not existing_mod_found: o.modifiers.remove(def_mod)
            self.restore_shape_key_settings(context, o, stored_tgt_settings)
            if existing_mod_found and mute_existing_mod:
                def_mod.show_viewport = False
            if sld_mod: sld_mod.show_viewport = True
        
        if use_sld_mod: obj_src.modifiers.remove(sld_mod)
        context.view_layer.objects.active = obj_src 
        self.restore_shape_key_settings(context, obj_src, stored_source_settings)

        return ret
        
        
    def execute(self, context):
        vg_enum_callback(context)
        vg_n = None if self.vg_name == 'NONE' else self.vg_name[:-3]
        
        self.process(context, self.use_existing_mod, self.mute_existing_mod,
                     self.move_to_first, self.precision, vg_n, self.vg_invert,
                     self.add_drivers, self.ignore_muted, self.suppress, self.overwrite,
                     self.use_sld_mod, self.sld_thickness, self.sld_offset)
        
        return {'FINISHED'}
    
    
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "use_existing_mod")
        ex_col = layout.column()
        ex_col.enabled = self.use_existing_mod
        ex_col.prop(self, "mute_existing_mod")
        
        layout.separator(factor=1)
        
        layout.label(text = "Fallback Mesh Deform Settings")
        def_box = layout.box()
        def_box.prop(self, "move_to_first")
        def_box.prop(self, "precision")
        vg_row = def_box.row()
        vg_row.prop(self, "vg_name")
        vg_row.prop(self, "vg_invert", icon="ARROW_LEFTRIGHT")

        layout.label(text = "Shape Key Settings")
        sk_box = layout.box()
        sk_box.prop(self, "add_drivers")
        sk_box.prop(self, "ignore_muted")
        sk_box.prop(self, "suppress")
        sk_box.prop(self, "overwrite")
        
        layout.label(text = "Solidify Settings")
        sld_box = layout.box()
        sld_box.prop(self, "use_sld_mod")
        sld_col = sld_box.column()
        sld_col.enabled = self.use_sld_mod
        sld_col.prop(self, "sld_thickness")
        sld_col.prop(self, "sld_offset")
    

# 3Dview Header Menu
class VIEW3D_MT_transfershapekeys_menu(bpy.types.Menu):
    bl_label = "Transfer Shape Keys"
    bl_idname = "VIEW3D_MT_transfershapekeys_menu"

    def draw(self, context):
        layout = self.layout
        
        layout.operator(TransferShapeKeysViaSurfaceDeform.bl_idname, text='Via Surface Deform', icon='MOD_MESHDEFORM')
        layout.operator(TransferShapeKeysViaMeshDeform.bl_idname, text='Via Mesh Deform', icon='MOD_MESHDEFORM')


classes = [
    VIEW3D_MT_transfershapekeys_menu,
    TransferShapeKeysViaSurfaceDeform,
    TransferShapeKeysViaMeshDeform,
]
    
def menu_func(self, context):
    self.layout.menu(VIEW3D_MT_transfershapekeys_menu.bl_idname)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


  
if __name__ == "__main__":
    register()
