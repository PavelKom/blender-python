import bpy
import re

# Regular expressions
re_num = re.compile('\[[-+]?\d+\]') # ["name of object"]   for  data["key"]
re_block = re.compile('[a-zA-Z0-9_]+') # property or method    for  data.key

def is_parent_rec(obj, p, allow_self=False):
    # Check the p is parent of obj. obj->obj2->obj3->p
    #print(obj, type(obj))
    if allow_self and obj == p:
        return True
    elif type(obj) not in (bpy.types.Armature, bpy.types.Key):
        if obj.parent is None:
            return False
        elif obj.parent == p:
            return True
        return is_parent_rec(obj.parent, p)
    return False

def get_all_child_obj(p):
    # Get all childrens of p
    childs = []
    for collection in bpy.data.collections:
        for obj in collection.all_objects:
            if is_parent_rec(obj, p):
                childs.append(obj)
    return childs

def get_armature(obj):
    # Get armature of current object (mesh or something)
    if obj.type == "ARMATURE":
        return obj
    if obj.parent is None:
        return None
    return get_armature(obj.parent)

def get_stuff(context):
    obj_data = None
    pose_bones = None         
    if context.active_object.data.get("rig_id") is None:
        # a non-rig child of the main rig is selected
        if context.active_object.parent is not None:
            obj_data = context.active_object.parent.data
            pose_bones = context.active_object.parent.pose.bones
        else:
            obj_data = context.active_object.data
            if context.active_object.pose is not None:
                pose_bones = context.active_object.pose.bones
    else:
        # the main rig is selected
        obj_data = context.active_object.data
        pose_bones = context.active_object.pose.bones
    return obj_data, pose_bones

def find_drivers(sel):
    # Get all objects with drivers
    objs = []
    for obj in sel:
        try:
            obj.animation_data.drivers    
        except:
            pass
        else:
            objs.append(obj)
    return objs


def get_driver_paths(obj):
    # Get all drivers (associated id object, path) from obj
    paths = []
    # Get drivers in Object
    try:
        for drv in obj.animation_data.drivers:
            for var in drv.driver.variables:
                for target in var.targets:
                    raw_path = target.data_path
                    if raw_path == "":
                        continue
                    paths.append((target.id, raw_path))
    except:
        pass
    if obj and obj.data:
        try:
            mats = obj.data.materials
            for mat in mats:
                if not mat.use_nodes or mat.node_tree.animation_data is None:
                    continue
                for drv in mat.node_tree.animation_data.drivers:
                    for var in drv.driver.variables:
                        for target in var.targets:
                            raw_path = target.data_path
                            if raw_path == "":
                                continue
                            paths.append((target.id, raw_path))
        except:
            pass
    return paths


def get_nodes_from_material():
    for m in bpy.data.materials:
         if m.use_nodes and m.node_tree.animation_data:
             for d in m.node_tree.animation_data.drivers:
                 for var in d.driver.variables:
                    for target in var.targets:
                        raw_path = target.data_path

def remove_dupes(i):
    # Remove duplicates from list
    return list(set(i))

def get_obj(name):
    # Get object or object.data by name
    for obj in bpy.data.objects:
        if obj.name == name:
            return obj
        elif obj.data is not None and obj.data.name == name:
            return obj
    return None


def get_prop_from_obj(index, layout, obj, blocks):
    # Def draw layout.prop for driver
    try:
        if type(blocks[-1]) == int:
            if blocks[-2][0] == ".":
                blocks[-2] = blocks[-2][1:]
            layout.prop(
                eval("obj" + "".join(blocks[:-2])), blocks[-2],
                index=blocks[-1], text= "")
            return
        elif blocks[-1].startswith("."):
            blocks[-1] = blocks[-1][1:]
        layout.prop(
            eval("obj" + "".join(blocks[:-1])), blocks[-1],
            text= "")
        return None
    except Exception as e:
        return e


def get_sub_blocks(data):
    # Split drivers data_path from a.b["c"][d] to list(a,b,'["c"]','[d]')
    # If drivers path is invalid, return exception for label
    blocks = []
    k = 0
    buf = data
    while 0 < len(data):
        if data[0] == "[":
            i = data.find("]") + 1
            if re_num.fullmatch(data[:i]):
                blocks.append(int(data[:i].replace("[","").replace("]","")))
            else:
                blocks.append(data[:i])
            data = data[i:]
        if len(data) > 0 and data[0] == ".":
            data = data[1:]
        res = re_block.search(data)
        if res is not None and res.span()[0] == 0:
            blocks.append("."+res[0])
            data = data[len(res[0]):]
        if buf == data:
            break
        buf = data
        if k > 20:
            break
    return blocks

def get_drivers_by_space(fcurves):
    drivers = []
    for fcurve in fcurves:
        if fcurve.driver:
            for var in fcurve.driver.variables:
                for target in var.targets:
                    print(target.id, target.data_path)
                    if target.data_path == "":
                        continue
                    if target.id is None:
                        continue
                    drivers.append((target.id, target.data_path))
    return drivers

def get_ALL_drivers():
    drivers = []
    data = bpy.data
    for groups in (data.actions, data.armatures, data.cache_files, data.cameras,
                   data.curves, data.fonts, data.grease_pencils, data.hair_curves,
                   data.lattices, data.libraries, data.lightprobes, data.lights,
                   data.linestyles, data.masks, data.materials, data.meshes, data.metaballs,
                   data.movieclips, data.node_groups, data.objects, data.paint_curves,
                   data.particles, data.pointclouds, data.scenes, data.shape_keys,
                   data.sounds, data.speakers, data.textures, data.volumes,
                   data.worlds):
        for group in groups:
            if groups == data.actions:
                drivers.extend(get_drivers_by_space(group.fcurves))
                for gr in group.groups:
                    drivers.extend(get_drivers_by_space(gr.channels))
            elif groups == data.materials:
                if group.use_nodes and group.node_tree.animation_data:
                    drivers.extend(get_drivers_by_space(group.node_tree.animation_data.drivers))
            if groups not in (data.actions,) and group.animation_data:
                drivers.extend(get_drivers_by_space(group.animation_data.drivers))
                if group.animation_data.nla_tracks:
                    for track in group.animation_data.nla_tracks:
                        for strip in track.strips:
                            drivers.extend(get_drivers_by_space(strip.fcurves))
                            
    drivers = remove_dupes(drivers)
    drivers.sort(key=drv_sort)
    return drivers

cached_blocks = {}
cached_drivers = []

class OPERATOR_Dump_Drivers_ALL(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.dump_drivers_all"
    bl_label = "Get ALL Drivers UI (to clipboard)"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        _obj = get_armature(context.active_object)
        if _obj is None:
            _obj = context.active_object
        obj = _obj.data
        
        drivers = get_ALL_drivers()
        curr_obj = ""
        box = None
        obj_path = ""
        dump = []
        dump.append("# Autogenerated props from ALL drivers")
        dump.append("col = self.layout.column()")
        for driver_name in drivers:
            if obj_path != repr(driver_name[0].id_data):
                obj_path = repr(driver_name[0].id_data)
                dump.append("# Drivers from %s" % (driver_name[0].name))
                dump.append("curr_obj = %s" % (obj_path))
            
            blocks = get_sub_blocks(driver_name[1])
            if type(blocks[-1]) == int:
                if blocks[-2][0] == ".":
                    blocks[-2] = blocks[-2][1:]
                dump.append(
                    "col.prop(curr_obj%s, %s, index=%i)" % (
                        "".join(blocks[:-2]), blocks[-2], blocks[-1]))
            else:
                if blocks[-1][0] == ".":
                    blocks[-1] = blocks[-1][1:]
                dump.append(
                    "col.prop(curr_obj%s, %s)" % (
                        "".join(blocks[:-1]), blocks[-1]))
        dump.append("# End of autogenerated code")
        res = "\n".join(dump)
        bpy.context.window_manager.clipboard = res
        print(res)
        return {'FINISHED'}

class OPERATOR_Dump_Drivers(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.dump_drivers_from_object"
    bl_label = "Get Drivers UI (to clipboard)"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        _obj = get_armature(context.active_object)
        if _obj is None:
            _obj = context.active_object
        obj = _obj.data
        
        drivers = get_ALL_drivers()
        curr_obj = ""
        box = None
        obj_path = ""
        dump = []
        dump.append("# Autogenerated props from drivers")
        dump.append("col = self.layout.column()")
        for driver_name in drivers:
            if is_parent_rec(driver_name[0], obj, True) or is_parent_rec(driver_name[0], _obj, True):
                if obj_path != repr(driver_name[0].id_data):
                    obj_path = repr(driver_name[0].id_data)
                    dump.append("# Drivers from %s" % (driver_name[0].name))
                    dump.append("curr_obj = %s" % (obj_path))
                
                blocks = get_sub_blocks(driver_name[1])
                if type(blocks[-1]) == int:
                    if blocks[-2][0] == ".":
                        blocks[-2] = blocks[-2][1:]
                    dump.append(
                        "col.prop(curr_obj%s, %s, index=%i)" % (
                            "".join(blocks[:-2]), blocks[-2], blocks[-1]))
                else:
                    if blocks[-1][0] == ".":
                        blocks[-1] = blocks[-1][1:]
                    dump.append(
                        "col.prop(curr_obj%s, %s)" % (
                            "".join(blocks[:-1]), blocks[-1]))
        dump.append("# End of autogenerated code")
        res = "\n".join(dump)
        bpy.context.window_manager.clipboard = res
        print(res)
        return {'FINISHED'}

class OPERATOR_Clear_cached_blocks(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.clear_cached_blocks"
    bl_label = "Update"

    @classmethod
    def poll(cls, context):
        #obj = context.active_object
        return True

    def execute(self, context):
        cached_blocks.clear() 
        cached_drivers.clear()
        return {'FINISHED'}


def drv_sort(e):
    return e[0].name + "  " + e[1]

rig_id = "easy_rig_checker"

class EasyRigChecker(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Easy RIG Checker"
    bl_idname = "VIEW3D_PT_rig_layers_" + rig_id
    bl_category = 'Item'
    
    @classmethod
    def poll(self, context):
        try:
            #sel = list(set([get_armature(o) for o in bpy.context.selected_objects]))
            sel = bpy.context.selected_objects
            return len(sel) > 0 and sel[0] is not None
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        obj_data, pose_bones = get_stuff(context)
        _obj = get_armature(context.active_object)
        if _obj is None:
            _obj = context.active_object
        obj = _obj.data
        
        #drivers = []
        #for o in find_drivers(get_all_child_obj(_obj)):
        #    drivers.extend(get_driver_paths(o))
        
        layout = self.layout
        col_root = layout.column()
        row = col_root.row()
        row.operator(OPERATOR_Clear_cached_blocks.bl_idname)
        row = col_root.row()
        row.operator(OPERATOR_Dump_Drivers.bl_idname)
        row.operator(OPERATOR_Dump_Drivers_ALL.bl_idname)
        col = col_root.box().column()
        col.row().label(text="-- Drivers --")
        #drivers = remove_dupes(drivers)
        #drivers.sort(key=drv_sort)
        global cached_drivers
        if len(cached_drivers) == 0:
            cached_drivers = get_ALL_drivers()
        curr_obj = ""
        box = None
        n = 1
        for driver_name in cached_drivers:
            if is_parent_rec(driver_name[0], obj, True) or is_parent_rec(driver_name[0], _obj, True):
                if curr_obj != driver_name[0].name:
                    box = col.box()
                    curr_obj = driver_name[0].name
                    n = 1
                row = box.row()
                key = "%i %s" % (n, driver_name[0].name+"  "+driver_name[1])
                row.label(text=key)
                if cached_blocks.get(key) is None:
                    cached_blocks[key] = get_sub_blocks(driver_name[1])
                res = get_prop_from_obj(n, row, driver_name[0], cached_blocks[key])
                if res is not None:
                    box.row().label(text="    %s" % (res))
                n += 1
            
            
        col.row().label(text="-- END --")
        
def register():
    bpy.utils.register_class(OPERATOR_Clear_cached_blocks)
    bpy.utils.register_class(OPERATOR_Dump_Drivers_ALL)
    bpy.utils.register_class(OPERATOR_Dump_Drivers)
    bpy.utils.register_class(EasyRigChecker)


def unregister():
    bpy.utils.unregister_class(OPERATOR_Clear_cached_blocks)
    bpy.utils.unregister_class(OPERATOR_Dump_Drivers_ALL)
    bpy.utils.unregister_class(OPERATOR_Dump_Drivers)
    bpy.utils.unregister_class(EasyRigChecker)



try:
    unregister()
except:
    pass
register()
