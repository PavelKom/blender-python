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

def test_prop(obj, blocks):
    val = ""
    if type(blocks[-1]) is int:
        val = "obj%s%s%s[%i]" %(
            "".join(blocks[:-2]),
            "" if blocks[-2][0] in ("[", ".") else ".",
            blocks[-2],
            blocks[-1]
        )
    else:
        val = "obj%s%s%s" %(
            "".join(blocks[:-1]),
            "" if blocks[-1][0] in ("[", ".") else ".",
            blocks[-1]
        )
    try:
        eval(val)
        return True
    except Exception as e:
        #print(obj, blocks, "\n",e, "\n", val)
        return False

def get_prop_type(obj, blocks):
    val = ""
    if type(blocks[-1]) is int:
        val = "obj%s%s%s[%i]" %(
            "".join(blocks[:-2]),
            "" if blocks[-2][0] in ("[", ".") else ".",
            blocks[-2],
            blocks[-1]
        )
    else:
        val = "obj%s%s%s" %(
            "".join(blocks[:-1]),
            "" if blocks[-1][0] in ("[", ".") else ".",
            blocks[-1]
        )
    if test_prop(obj, blocks):
        return type(eval(val))
    else:
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
                    if target.data_path == "":
                        continue
                    if target.id is None:
                        continue
                    if fcurve.data_path[0] == "[":
                        d = repr(fcurve.id_data) + fcurve.data_path
                    else:
                        d = repr(fcurve.id_data) + "." + fcurve.data_path
                    drivers.append((target.id, target.data_path, d.replace("'",'"')))
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
            if groups not in (data.actions, data.fonts, data.libraries) and group.animation_data:
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

class DriverFinderUIPropertyGroup(bpy.types.PropertyGroup):
    show_from_all : bpy.props.BoolProperty(
        name="From ALL objects",
        default=False
        )
    show_broken : bpy.props.BoolProperty(
        name="Show broken",
        default=True
        )
    show_valid : bpy.props.BoolProperty(
        name="Show valid",
        default=True
        )
    show_int : bpy.props.BoolProperty(
        name="int",
        default=True
        )
    show_float : bpy.props.BoolProperty(
        name="float",
        default=True
        )
    show_bool : bpy.props.BoolProperty(
        name="bool",
        default=True
        )
    show_str : bpy.props.BoolProperty(
        name="str",
        default=True
        )
    show_others : bpy.props.BoolProperty(
        name="Others",
        default=True
        )
    # Globals
    prop_scene : bpy.props.BoolProperty(
        name="Scene",
        default=False
        )
    prop_world : bpy.props.BoolProperty(
        name="World",
        default=False
        )
    prop_collections : bpy.props.BoolProperty(
        name="Collections",
        default=False
        )
    # Locals
    prop_objects : bpy.props.BoolProperty(
        name="Objects",
        default=False
        )
    prop_data : bpy.props.BoolProperty(
        name="Data",
        default=False
        )
    prop_posebones : bpy.props.BoolProperty(
        name="PoseBones",
        default=False
        )
    prop_bones : bpy.props.BoolProperty(
        name="Bones",
        default=False
        )
    # Misc
    prop_mats : bpy.props.BoolProperty(
        name="Materials",
        default=False
        )

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
    return e[0].name + "  " + e[1] + "  " + e[2]

class EasyRigChecker(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Easy RIG Checker"
    bl_idname = "VIEW3D_PT_asy_rig_checker"
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
        dfui_props = bpy.context.scene.dfui_props
        
        layout = self.layout
        col_root = layout.column()
        row = col_root.row()
        row.operator(OPERATOR_Clear_cached_blocks.bl_idname)
        row.prop(dfui_props, "show_from_all")
        row.prop(dfui_props, "show_broken")
        row.prop(dfui_props, "show_valid")
        row = col_root.row()
        row.prop(dfui_props, "show_int")
        row.prop(dfui_props, "show_float")
        row.prop(dfui_props, "show_bool")
        row.prop(dfui_props, "show_str")
        row.prop(dfui_props, "show_others")
        row = col_root.row()
        row.operator(OPERATOR_Dump_Drivers.bl_idname)
        row.operator(OPERATOR_Dump_Drivers_ALL.bl_idname)
        col = col_root.box().column()
        global cached_drivers
        if len(cached_drivers) == 0:
            cached_drivers = get_ALL_drivers()
        col.row().label(text="-- Drivers (%i) --" % (len(cached_drivers)))
        #drivers = remove_dupes(drivers)
        #drivers.sort(key=drv_sort)
        curr_obj = ""
        box = None
        n = 1
        for driver_name in cached_drivers:
            if not dfui_props.show_from_all and not (is_parent_rec(driver_name[0], obj, True) or is_parent_rec(driver_name[0], _obj, True)):
                continue
            if curr_obj != driver_name[0].name:
                box = col.box()
                curr_obj = driver_name[0].name
                n = 1
            key = "%i %s %s %s" % (n, driver_name[0].name, driver_name[1], driver_name[2])
            if cached_blocks.get(key) is None:
                cached_blocks[key] = get_sub_blocks(driver_name[1])
            if test_prop(driver_name[0], cached_blocks[key]):
                if not dfui_props.show_valid:
                    continue
            elif not dfui_props.show_broken:
                continue
            prop_type = get_prop_type(driver_name[0], cached_blocks[key])
            if prop_type == int and not dfui_props.show_int:
                continue
            elif prop_type == float and not dfui_props.show_float:
                continue
            elif prop_type == bool and not dfui_props.show_bool:
                continue
            elif prop_type == str and not dfui_props.show_str:
                continue
            elif prop_type not in (int, float, bool, str) and not dfui_props.show_others:
                continue
            _box = box.box()
            _box.row().label(text="%i  %s" % (n, driver_name[2]))
            _box.row().label(text="%s%s%s" % (driver_name[0].name, "" if driver_name[1][0] == "[" else ".", driver_name[1]))
            res = get_prop_from_obj(n, _box.row(), driver_name[0], cached_blocks[key])
            if res is not None:
                box.row().label(text="    %s" % (res))
            n += 1
        col.row().label(text="-- END --")
        

def prop_is_useless(path):
    global cached_drivers
    if len(cached_drivers) == 0:
        cached_drivers = get_ALL_drivers()
    for driver in cached_drivers:
        p1 = repr(driver[0])
        if driver[1][0] != "[":
            p1 += "."
        p1 += driver[1]
        p1 = p1.replace("'",'"')
        if p1 == path or driver[2] == path:
            return False
    return True


    
def get_DEL_items(self, context):
    items = (
        ("PROP","Property","One Prop"),
        ("OBJECT","Object","All Props on Object"),
        #("BONES","Bones","Props from all Bones"),
        #("POSEBONES","PoseBones","Props from all PoseBones"),
        #("BONE","Bone","Props from simple Bone"),
        #("POSEBONE","PoseBone","Props from simple PoseBone"),
        #("COLLECTION","Collection","Collection of Objects"),
    )
    return items
    
class DELETE_UselessProp(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.delete_useless_property"
    bl_label = "DELETE"
    
    #id_obj : bpy.props.PointerProperty()
    obj : bpy.props.StringProperty()
    prop : bpy.props.StringProperty()
    group : bpy.props.EnumProperty(items=get_DEL_items)
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = eval(self.obj)
        match self.group:
            case 'PROP':
                eval(self.obj+'.pop("'+self.prop+'")')
            case 'OBJECT':
                props = [*obj.keys()]
                for prop in props:
                    path = (repr(obj)+"['"+prop+"']").replace("'",'"')
                    if prop_is_useless(path):
                        eval(self.obj+'.pop("'+prop+'")')
        return {'FINISHED'}

class UselessPropChecker(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Useless Prop Checker"
    bl_idname = "VIEW3D_PT_useless_prop_checker"
    bl_category = 'Item'
    
    buf_num : bpy.props.IntProperty()
    
    @classmethod
    def poll(self, context):
        try:
            #sel = list(set([get_armature(o) for o in bpy.context.selected_objects]))
            sel = bpy.context.selected_objects
            return len(sel) > 0 and sel[0] is not None
        except (AttributeError, KeyError, TypeError):
            return False

    def draw(self, context):
        sel = bpy.context.selected_objects
        dfui_props = bpy.context.scene.dfui_props
        layout = self.layout
        col_root = layout.column()
        row = col_root.row()
        row.operator(OPERATOR_Clear_cached_blocks.bl_idname)
        row.prop(dfui_props, "prop_world")
        row.prop(dfui_props, "prop_scene")
        row.prop(dfui_props, "prop_collections")
        row = col_root.row()
        row.prop(dfui_props, "prop_objects")
        row.prop(dfui_props, "prop_data")
        row.prop(dfui_props, "prop_bones")
        row.prop(dfui_props, "prop_posebones")
        row = col_root.row()
        row.prop(dfui_props, "prop_mats")
        colls = []
        if dfui_props.prop_world:
            colls.append(("Worlds:", bpy.data.worlds))
        if dfui_props.prop_scene:
            colls.append(("Scenes:", bpy.data.scenes))
        if dfui_props.prop_collections:
            colls.append(("Collections:", bpy.data.collections))
        if dfui_props.prop_objects:
            colls.append(("Objects:", bpy.data.objects))
        if dfui_props.prop_mats:
            colls.append(("Materials:", bpy.data.materials))
        if dfui_props.prop_data:
            objs = []
            for obj in bpy.data.objects:
                objs.append(obj.data)
            colls.append(("Objects Data:", objs))
        if dfui_props.prop_bones:
            objs = []
            for obj in bpy.data.armatures:
                for bone in obj.bones:
                    objs.append(bone)
            colls.append(("Bones:", objs))
        if dfui_props.prop_posebones:
            objs = []
            for obj in bpy.data.objects:
                if obj.type != 'ARMATURE':
                    continue
                for bone in obj.pose.bones:
                    objs.append(bone)
            colls.append(("Bones:", objs))
        
        main_row = col_root.row()
        buf_num = 0
        for lbl, coll in colls:
            c_box = None
            for obj in coll:
                o_box = None
                _wbox = None
                for prop in obj.keys():
                    path = (repr(obj)+"['"+prop+"']").replace("'",'"')
                    if prop_is_useless(path):
                        if c_box is None:
                            c_box = col_root.box()
                            c_box.label(text=lbl)
                        if o_box is None:
                            o_box = c_box.box()
                            o_row = o_box.row()
                            splitter = o_row.split(factor=0.8)
                            splitter.label(text=obj.name)
                            _op = splitter.operator(DELETE_UselessProp.bl_idname)
                            _op.obj = repr(obj)
                            _op.group = 'OBJECT'
                        if _wbox is None:
                            _wbox = o_box.box()
                        _wrow = _wbox.row()
                        splitter = _wbox.split(factor=0.8)
                        splitter.label(text=path)
                        op = splitter.operator(DELETE_UselessProp.bl_idname)
                        op.obj = repr(obj)
                        op.prop = prop
                        op.group = 'PROP'
                        buf_num += 1
        main_row.label(text="Current useless props: %i" % (buf_num))
            
        '''
        if dfui_props.prop_world:
            wwbox = col_root.box()
            wwbox.label(text="Worlds:")
            for world in bpy.data.worlds:
                wbox = wwbox.box()
                wbox.label(text=world.name)
                _wbox = None
                for prop in world.keys():
                    path = (repr(world)+"['"+prop+"']").replace("'",'"')
                    if prop_is_useless(path):
                        if _wbox is None:
                            _wbox = wbox.box()
                        _wbox.label(text=path)
        '''
        
        
def register():
    bpy.utils.register_class(DriverFinderUIPropertyGroup)
    bpy.utils.register_class(OPERATOR_Clear_cached_blocks)
    bpy.utils.register_class(OPERATOR_Dump_Drivers_ALL)
    bpy.utils.register_class(OPERATOR_Dump_Drivers)
    bpy.utils.register_class(EasyRigChecker)
    bpy.utils.register_class(UselessPropChecker)
    bpy.utils.register_class(DELETE_UselessProp)
    bpy.types.Scene.dfui_props = bpy.props.PointerProperty(type=DriverFinderUIPropertyGroup)


def unregister():
    bpy.utils.unregister_class(DriverFinderUIPropertyGroup)
    bpy.utils.unregister_class(OPERATOR_Clear_cached_blocks)
    bpy.utils.unregister_class(OPERATOR_Dump_Drivers_ALL)
    bpy.utils.unregister_class(OPERATOR_Dump_Drivers)
    bpy.utils.unregister_class(EasyRigChecker)
    bpy.utils.unregister_class(UselessPropChecker)
    bpy.utils.unregister_class(DELETE_UselessProp)



try:
    unregister()
except:
    pass
register()