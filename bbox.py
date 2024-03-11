import bpy, bmesh, re
from bpy.types import MeshVertices
from mathutils import Vector, Matrix, Euler


scene = bpy.context.scene
vec_zero = Vector((0.0,0.0,0.0))
vec_zero.freeze()
vec_one = Vector((1.0,1.0,1.0))
vec_one.freeze()
rot_zero = Euler((0.0,0.0,0.0))
rot_zero.freeze()

# Convert list of verticles to list of Vector
def vtx_to_vec(vtx):
    """
    Convert MeshVertex/MeshVertices position(s) to (array of) vector(s)
    """
    if isinstance(vtx.rna_type, MeshVertices):
        return [v.co for v in vtx]
    elif isinstance(vtx.rna_type, MeshVertex):
        return vtx.co
    raise TypeError("ONLY VERTEXT OR VERTICES")
    

def v_min_max(vecs):
    """
    Get 2 points defining the diagonal of the bounding box
    """
    xs = [v.x for v in vecs]
    ys = [v.y for v in vecs]
    zs = [v.z for v in vecs]
    return Vector((min(xs), min(ys), min(zs))), Vector(( max(xs), max(ys), max(zs)))

def v_shuffles(vecs):
    """
    Get a list of vectors by shuffling coordinates
    """
    xs = [v.x for v in vecs]
    ys = [v.y for v in vecs]
    zs = [v.z for v in vecs]
    res = []
    for x in xs:
        for y in ys:
            for z in zs:
                res.append(Vector((x, y, z)))
    return res

def get_bbox(vertx):
    """
    Get bounding box data: corners, size, origin
    """
    v1, v2 = v_min_max(vtx_to_vec(vertx))
    size = Vector((
        abs(v2.x - v1.x),
        abs(v2.y - v1.y),
        abs(v2.z - v1.z)
    ))
    origin = Vector(( (v2.x+v1.x)/2.0 , (v2.y+v1.y)/2.0, v1.z ))
    return v_shuffles((v1, v2)), size, origin

def approx(test, values, appr=0.000001):
    """
    Check if the value is approximated by other values
    """
    for val in values:
        if abs(val - test) < appr:
            return True
    return False

def mesh_buildpoly(_obj):
    """
    Build polygons on mesh
    """
    previous_context = bpy.context.area.type
    
    bpy.context.view_layer.objects.active = None
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    
    for v in _obj.data.vertices:
        v.select = True
    bpy.ops.mesh.edge_face_add()
    
    _obj.select_set(False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.area.type = previous_context


def get_object_bb(obj, prefix: str="BBOX", create_bbox=True, transform=True, move=True, rotate=True, scale=True, polygon=True, parent=False):
    """
    Create Bounding Box of object and/or move object to world zero
    """
    mesh = obj.data if transform else bpy.data.meshes.new_from_object(obj)
    
    transform = False if parent else transform
    move =False if parent else move
    rotate=False if parent else rotate
    scale=False if parent else scale
    
    tr_matrix = Matrix.LocRotScale(obj.location, obj.rotation_euler, obj.scale) if transform else Matrix.LocRotScale(
        vec_zero, rot_zero, vec_one)
    mesh.transform(tr_matrix)
    
    if transform:
        obj.scale = (1.0,1.0,1.0)
        obj.location = (0.0,0.0,0.0)
        obj.rotation_euler = (0.0,0.0,0.0)
    
    bb_vertex, n_len, origin = get_bbox(mesh.vertices)
    mesh.transform(Matrix.Translation(-origin))
    
    if create_bbox:
        if bpy.data.collections.get(obj.name) is None:
            coll = bpy.data.collections.new(obj.name)
            bpy.context.scene.collection.children.link(coll)
        try:
            bpy.data.collections[obj.name].objects.link(obj)
        except RuntimeError:
            pass
                        
        bb_mesh = bpy.data.meshes.new(prefix + mesh.name)
        bbox = bpy.data.objects.new(bb_mesh.name, bb_mesh)
        bpy.data.collections[obj.name].objects.link(bbox)
        edges = []
        for i in range(len(bb_vertex)-1):
            for j in range(i+1, len(bb_vertex)):
                if approx((bb_vertex[j]-bb_vertex[i]).length, n_len, 0.01):
                    edges.append((i,j))
        bb_mesh.clear_geometry()
        bb_mesh.from_pydata(bb_vertex, edges, [])
        if transform:
            bb_mesh.transform(Matrix.Translation(-origin))
            bbox.matrix_world.translation += origin
            bbox.location -= origin
        else:
            bbox.location = obj.location if move else bbox.location
            bbox.rotation_euler = obj.rotation_euler if rotate else bbox.rotation_euler
            bbox.scale = obj.scale if scale else bbox.scale
        if parent:
            bbox.parent = obj
            bbox.matrix_parent_inverse = obj.matrix_world.inverted()
        if polygon:
            mesh_buildpoly(bbox)
    if not transform:
        bpy.data.meshes.remove(mesh)
    

# For testing
#get_object_bb(bpy.data.objects[0])



class BBoxPropertyGroup(bpy.types.PropertyGroup):
    bbox_createbbox : bpy.props.BoolProperty(
        name="Create BBox",
        default=True
        )
    bbox_createname : bpy.props.StringProperty(
        name="BBox name prefix",
        default="BBOX.",
        description="BBox name prefix"
        )
    bbox_transform : bpy.props.BoolProperty(
        name="Transform to Zero",
        default=True
        )
    bbox_move : bpy.props.BoolProperty(
        name="Move",
        default=True
        )
    bbox_rotate : bpy.props.BoolProperty(
        name="Rotate",
        default=True
        )
    bbox_scale : bpy.props.BoolProperty(
        name="Scale",
        default=True
        )
    bbox_polygon : bpy.props.BoolProperty(
        name="Polygon",
        default=True
        )
    bbox_visible : bpy.props.BoolProperty(
        name="Only visible",
        default=True
        )
    bbox_render : bpy.props.BoolProperty(
        name="Only render",
        default=True
        )
    bbox_selectall : bpy.props.BoolProperty(
        name="Select All",
        default=False
        )
    bbox_ignorebbox : bpy.props.BoolProperty(
        name="Ignore BBoxes. Used regex '.*%subname%.*'",
        default=True
        )
    bbox_ignorename : bpy.props.StringProperty(
        name="Bounding name sub-name. Used regex '.*%subname%.*'",
        default="BBOX",
        description="Bounding name sub-name. Used regex '.*%subname%.*'"
        )
    bbox_parent : bpy.props.BoolProperty(
        name="Parent BBox to object",
        default=False
        )


class BBoxButton(bpy.types.Operator):
    bl_label = "Evaluate"
    bl_idname = "bbox.button1"
    
    #def invoke(self, context, event):
    #    wm = context.window_manager
    #    return wm.invoke_props_dialog(self)
    
    def execute(self, context):
        if len(bpy.data.objects) == 0:
            self.report({'INFO'}, "[BBOX] Scene don't have any object")
            return {'FINISHED'}
        scene = bpy.context.scene
        bbox_props = scene.bbox_props
        bbox_name = re.compile(".*" + bbox_props.bbox_ignorename + ".*")
        names = []
        for obj in bpy.data.objects:
            if not isinstance(obj.data, bpy.types.Mesh):
                continue
            # Skip unselected objects
            elif not obj.select_get() and not bbox_props.bbox_selectall:
                continue
            # Skip invisible object
            elif not obj.visible_get() and bbox_props.bbox_visible:
                continue
            # Skip non-rendable objects
            elif obj.hide_render and bbox_props.bbox_render:
                continue
            # Skip bounding boxes
            elif bbox_props.bbox_ignorebbox and bbox_name.match(obj.name) is not None:
                continue
            get_object_bb(obj, bbox_props.bbox_createname, bbox_props.bbox_createbbox,
                bbox_props.bbox_transform,
                bbox_props.bbox_move, bbox_props.bbox_rotate, bbox_props.bbox_scale,
                bbox_props.bbox_polygon, bbox_props.bbox_parent)
            names.append(obj.name)
        if len(names) == 0:
            names.append("NOTHING!!!")
        self.report({'INFO'}, "[BBOX] Evaluated for: %s" % ", ".join(names))
        return {'FINISHED'}


class BBoxPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Bounding Box"
    #bl_idname = "OBJECT_PT_BBOX"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    #bl_context = "object"

    def draw(self, context):
        layout = self.layout
        bbox_props = scene.bbox_props
        
        # Create bbox
        layout.operator(BBoxButton.bl_idname) # Button
        box = layout.box()
        box.prop(bbox_props, "bbox_createbbox", text="Create BBox | BBox name prefix")
        row = box.row()
        row.active = bbox_props.bbox_createbbox
        row.prop(bbox_props, "bbox_createname", text="")
        
        # Transform
        row = layout.row()
        column = row.column()
        column.prop(bbox_props, "bbox_transform")
        column.prop(bbox_props, "bbox_polygon")
        column.prop(bbox_props, "bbox_selectall")
        column = row.column()
        column.enabled = not bbox_props.bbox_transform
        column.prop(bbox_props, "bbox_move")
        column.prop(bbox_props, "bbox_rotate")
        column.prop(bbox_props, "bbox_scale")
        
        # Visibility
        row = layout.box().row()
        row.prop(bbox_props, "bbox_visible")
        row.prop(bbox_props, "bbox_render")
        
        # Ignoring bboxes
        row = layout.row()
        row.prop(bbox_props, "bbox_ignorebbox", text="Ignore BBoxes")
        #row.prop(bbox_props, "bbox_parent", text="Parent")
        column = layout.column()
        column.enabled = bbox_props.bbox_ignorebbox
        column.label(text="As regex '.*%subname%.*'")
        column.prop(bbox_props, "bbox_ignorename", text="")
        
def register():
    bpy.utils.register_class(BBoxPropertyGroup)
    bpy.utils.register_class(BBoxButton)
    #bpy.utils.register_class(BBoxPanel)
    bpy.types.Scene.bbox_props = bpy.props.PointerProperty(type=BBoxPropertyGroup)
    # https://blender.stackexchange.com/questions/41933/bl-context-multiple-areas
    contexts = ["object", "scene"]
    for c in contexts:
        propdic = {"bl_idname": "OBJECT_PT_BBOX_%s" % c,
                   "bl_context": c,
                   }
        MyPanel = type("BBoxPanel_%s" % c, (BBoxPanel,), propdic)
        bpy.utils.register_class(MyPanel)


def unregister():
    bpy.utils.unregister_class(BBoxPropertyGroup)
    bpy.utils.unregister_class(BBoxButton)
    #bpy.utils.unregister_class(BBoxPanel)
    contexts = ["object", "scene"]
    for c in contexts:
        propdic = {"bl_idname": "OBJECT_PT_BBOX_%s" % c,
                   "bl_context": c,
                   }
        MyPanel = type("BBoxPanel_%s" % c, (BBoxPanel,), propdic)
        bpy.utils.unregister_class(MyPanel)
    del bpy.types.Scene.bbox_props


if __name__ == "__main__":
    register()
        
        
