bl_info = {
    "name": "SwiftBlock",
    "author": "Karl-Johan Nogenmyr, Mikko Folkersma, Turo Valikangas",
    "version": (0, 2),
    "blender": (2, 7, 7),
    "location": "View_3D > Object > SwiftBlock",
    "description": "Writes block geometry as blockMeshDict file",
    "warning": "",
    "wiki_url": "http://openfoamwiki.net/index.php/SwiftBlock",
    "tracker_url": "",
    "category": "OpenFOAM"}

import bpy
import bmesh
import time
import importlib
from . import blockBuilder
importlib.reload(blockBuilder)
from . import blender_utils
importlib.reload(blender_utils)
from . import utils
importlib.reload(utils)
from mathutils import Vector



# Create the swiftBlock panel
class SwiftBlockPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "SwiftBlock"
    bl_label = "SwiftBlock"

    def draw(self, context):
        scn = context.scene
        ob = context.active_object
        if not ob:
            return
        box = self.layout.column(align=True)

        if ob.ispreviewObject:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = True
        elif ob.blocking_object and ob.name != ob.blocking_object:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = False
        elif not ob.isblockingObject and ob.type == 'MESH':
            box.operator("init.blocking", text="Initialize blocking")

        elif context.active_object and bpy.context.active_object.mode == "EDIT":

            box = self.layout.box()
            box.prop(ob,"Mesher")
            box.operator("build.blocking", text="Build Blocking")

            split = box.split()
            split.operator("preview.mesh", text="Preview mesh")
            split = split.split()
            split.operator("write.mesh", text="Write mesh")
            box.template_list("block_items", "", ob, "blocks", ob, "block_index", rows=2)
            box.operator("get.block")

            box = self.layout.box()
            box.label("Line Mapping")
            # box.prop(ob, "MappingType")
            split = box.split()
            split.prop(ob, "Cells")
            if ob.Mesher == "blockMeshMG":
                split = box.split()
                col = split.column()
                col.label("Start")
                col.prop(ob, "x1")
                col.prop(ob, "r1")
                col = split.column()
                col.label("End")
                col.prop(ob, "x2")
                col.prop(ob, "r2")
            elif ob.Mesher == "blockMeshBodyFit":
                split.prop(ob, "Ratio")
            split = box.split()
            split.operator("set.edgemapping")
            split.operator("get.edge")
            split = box.split()
            split.operator("select.parallel")
            split.operator("flip.edges")
            if 'Edge_directions' in bpy.data.objects:
                box.operator("draw.directions",'Show edge directions',emboss=False,icon="CHECKBOX_HLT").show=False
            else:
                box.operator("draw.directions",'Show edge directions',emboss=False,icon="CHECKBOX_DEHLT").show=True

            box = self.layout.box()
            box.label("Projections")
            split = box.split()
            split.prop(ob, "ProjectionObject","",icon = "OUTLINER_OB_SURFACE")
            split.operator("add.projections", text="Add projections")
            box.operator("remove.projections", text="Remove projections")
            if ob.Mesher == "blockMeshBodyFit":
                box.prop(ob, 'SearchLength')
            box.template_list("projection_items", "", ob, "projections", ob, "projection_index", rows=2)
            if ob.Autosnap:
                split = box.split(percentage=0.1)
                split.prop(ob, "Autosnap", "")
                split = split.split(percentage=0.9)
                split.prop(ob, "EdgeSnapObject",'')
                if ob.EdgeSnapObject != "":
                    o = split.operator("activate.object","",emboss=False,icon="OBJECT_DATA")
                    o.ob = ob.EdgeSnapObject
            else:
                box.prop(ob, "Autosnap")

            box = self.layout.box()
            box.label('Boundary conditions')
            box.prop(ob, 'patchName')
            box.prop(ob, 'bcTypeEnum')
            box.operator("set.patchname")
            for m in ob.data.materials:
                try:
                    patchtype = str(' ' + m['patchtype'])
                    split = box.split(percentage=0.2, align=True)
                    col = split.column()
                    col.prop(m, "diffuse_color", text="")
                    col = split.column()
                    col.operator("set.getpatch", text=m.name + patchtype, emboss=False).whichPatch = m.name
                except:
                    pass
            box = self.layout.box()

            box.label("Edge groups")
            split = box.split(percentage=0.9)
            split.prop(ob, 'EdgeGroupName','')
            split.operator("add.edgegroup",'',icon='PLUS',emboss = False)
            for eg in ob.edge_groups:
                split = box.split(percentage=0.8, align=True)
                col = split.column()
                col.operator("get.edgegroup", eg.group_name , emboss=False).egName = eg.group_name
                col = split.column()
                col.operator('remove.edgegroup', '',emboss=False,icon='X').egName = eg.group_name


def initSwiftBlockProperties():
    bpy.types.Object.isblockingObject = bpy.props.BoolProperty(default=False)
    bpy.types.Object.blocking_object = bpy.props.StringProperty(default="")
    bpy.types.Object.preview_object = bpy.props.StringProperty(default="")
    bpy.types.Object.ispreviewObject = bpy.props.BoolProperty(default=False)
    bpy.types.Object.direction_object = bpy.props.StringProperty(default="")
    bpy.types.Object.isdirectionObject = bpy.props.BoolProperty(default=False)
    bpy.types.Object.isprojectionObject = bpy.props.BoolProperty(default=False)

    bpy.types.Object.Mesher = bpy.props.EnumProperty(name="",
            items = (("blockMeshMG","blockMeshMG","",1),
                     ("blockMeshBodyFit","blockMeshBodyFit","",2),),update=changeMesher)
# Mapping properties
    bpy.types.Object.MappingType = bpy.props.EnumProperty(name="",
            items = (("Geometric MG","Geometric MG","",1),
                     ("Geometric","Geometric","",2),))
    bpy.types.Object.Dx = bpy.props.FloatProperty(name="dx", default=1, update=setCellSize, min=0)
    bpy.types.Object.Cells = bpy.props.IntProperty(name="Cells", default=10,  min=1)
    bpy.types.Object.x1 = bpy.props.FloatProperty(name="x1", default=0, description="First cell size", min=0)
    bpy.types.Object.x2 = bpy.props.FloatProperty(name="x2", default=0, description="Last cell size",  min=0)
    bpy.types.Object.r1 = bpy.props.FloatProperty(name="r1", default=1.2, description="First boundary layer geometric ratio", min=1.0)
    bpy.types.Object.r2 = bpy.props.FloatProperty(name="r2", default=1.2, description="Last boundary layer geometric ratio", min=1.0)
    bpy.types.Object.Ratio = bpy.props.FloatProperty(name="Ratio", default=1.0, description="Ratio of first cell to last cell", min=0)
    bpy.types.Object.SearchLength = bpy.props.FloatProperty(name="Search Length", default=1.0, description="", min=0)
    # bpy.types.Object.ShowEdgeDirections = bpy.props.BoolProperty(name="Show directions", default=True, update = updateDirections, description="Show edge directions?")


# Blocking properties
    bpy.types.Object.blocks = \
        bpy.props.CollectionProperty(type=BlockProperty)
    bpy.types.Object.block_index = bpy.props.IntProperty()

# Boundary condition properties
    bpy.types.Object.bcTypeEnum = bpy.props.EnumProperty(
        items = [('wall', 'wall', 'Defines the patch as wall'),
                 ('patch', 'patch', 'Defines the patch as generic patch'),
                 ('empty', 'empty', 'Defines the patch as empty'),
                 ('symmetry', 'symmetry', 'Defines the patch as symmetry'),
                 ],
        name = "Patch type")
    bpy.types.Object.patchName = bpy.props.StringProperty(
        name = "Patch name",
        description = "Specify name of patch",
        default = "defaultName")

# Projection/snapping properties
    bpy.types.Object.projections = \
        bpy.props.CollectionProperty(type=ProjectionProperty)
    bpy.types.Object.projection_index = bpy.props.IntProperty()

    bpy.types.Object.Autosnap = bpy.props.BoolProperty(name="Automatic edge projection",
            description = "Snap lines automatically from geometry?")
    bpy.types.Object.ProjectionObject = bpy.props.EnumProperty(name="Projection object", 
            items=getProjectionObjects, description = "Projection object")
    bpy.types.Object.EdgeSnapObject = bpy.props.EnumProperty(name="Object", 
            items=getProjectionObjects, description = "Projection object")

# Edge group properties
    bpy.types.Object.edge_groups = \
        bpy.props.CollectionProperty(type=EdgeGroupProperty)
    bpy.types.Object.EdgeGroupName = bpy.props.StringProperty(
        name = "Name",default="group name",
        description = "Specify name of edge group")


# For the lists in GUI
class block_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.9)
        block = context.active_object.blocks[index]
        name = block.name + ' %d'%index
        c = split.operator("edit.block", name, emboss=False)
        c.blockid = index
        c.name = block.name

        if block.enabled:
            c = split.operator('enable.block', '',emboss=False,icon="CHECKBOX_HLT").blockid = index
        else:
            c = split.operator('enable.block','', emboss=False,icon="CHECKBOX_DEHLT").blockid = index

class projection_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.4)
        proj = context.active_object.projections[index]
        if proj.type == 'vert':
            icon = "VERTEXSEL"
        elif proj.type == 'edge':
            icon = "EDGESEL"
        elif proj.type == 'face':
            icon = "FACESEL"
        c = split.operator("get.projection", '{}{}'.format(proj.type[0],proj.id), emboss=False, icon=icon)
        c.type = proj.type
        c.id = proj.id
        split = split.split(0.6)
        c = split.operator("activate.object",proj.ob, emboss=False, icon="OBJECT_DATA")
        c.ob = proj.ob
        c = split.operator('remove.projection','', emboss = False, icon='X')
        c.proj_id = index


# Get all objects in current context
def getProjectionObjects(self, context):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not ob.isblockingObject and not ob.ispreviewObject and not ob.isdirectionObject:
            obs.append((ob.name, ob.name, ''))
    return obs


# SwiftBlock properties
class BlockProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    name = bpy.props.StringProperty()
    verts = bpy.props.IntVectorProperty(size = 8)
    enabled = bpy.props.BoolProperty(default=True)
    namedRegion = bpy.props.BoolProperty(default=False)
bpy.utils.register_class(BlockProperty)

class EdgeGroupProperty(bpy.types.PropertyGroup):
    group_name = bpy.props.StringProperty()
    group_edges = bpy.props.StringProperty()
bpy.utils.register_class(EdgeGroupProperty)

class ProjectionProperty(bpy.types.PropertyGroup):
    type = bpy.props.StringProperty() #vert,edge,face
    id = bpy.props.IntProperty() #bmesh id
    ob = bpy.props.StringProperty()
bpy.utils.register_class(ProjectionProperty)

# Initialize all the bmesh layer properties for the blocking object
class InitBlockingObject(bpy.types.Operator):
    bl_idname = "init.blocking"
    bl_label = "Init blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        print("initialize BMesh")

        bpy.ops.object.mode_set(mode='EDIT')
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        bm.edges.layers.string.new("type")
        bm.edges.layers.float.new("x1")
        bm.edges.layers.float.new("x2")
        bm.edges.layers.float.new("r1")
        bm.edges.layers.float.new("r2")
        bm.edges.layers.float.new("dx")
        bm.edges.layers.float.new("ratio")
        bm.edges.layers.int.new("cells")
        bm.edges.layers.int.new("groupid")
        bm.edges.layers.int.new("modtime")

        bm.faces.layers.int.new('pos')
        bm.faces.layers.int.new('neg')

        ob.blocks.clear()
        ob.projections.clear()
        ob.edge_groups.clear()

        ob.data.update()
        ob.isblockingObject = True
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.set.patchname('INVOKE_DEFAULT')
        bpy.ops.mesh.select_all(action="DESELECT")
        ob.show_all_edges = True
        ob.show_wire = True
        return {"FINISHED"}

# Blocking and previewing operators
# Automatically find blocking for the object and view it.
class BuildBlocking(bpy.types.Operator):
    bl_idname = "build.blocking"
    bl_label = "Build blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        ob = context.active_object
        mesh = ob.data

        verts = []
        edges = []

        edgeDict = dict()
        for v in mesh.vertices:
            verts.append(v.co)
        for e in mesh.edges:
            edges.append([e.vertices[0],e.vertices[1]])
            edgeDict[(e.vertices[0],e.vertices[1])] = e.index
        disabled = []

        # find blocking
        log, block_verts, block_edges, face_info, all_edges, faces_as_list_of_nodes = blockBuilder.blockFinder(edges,verts,disabled = disabled)

        ob.blocks.clear()
        for i,bv in enumerate(block_verts):
            b = ob.blocks.add()
            b.id = i
            b.name = 'block'#_{}'.format(i)
            b.verts = bv

        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        bm.verts.ensure_lookup_table()

        for i, g in enumerate(block_edges):
            for e in g:
                bme = bm.edges.get((bm.verts[e[0]],bm.verts[e[1]]))
                bme[groupl] = i

# A bug in face_info when there are o-grids. The block indices after o-grid block have to be decreased by one.
        replace_ids = dict()
        block_ids = []
        for key in face_info.keys():
            block_ids.extend(face_info[key]['pos'])
            block_ids.extend(face_info[key]['neg'])
        block_ids = sorted(set(block_ids))
        nblocks = len(ob.blocks)-1

        decrease = []
        if nblocks < max(block_ids):
            for i in range(max(block_ids)):
                if i not in block_ids:
                    decrease.append(i)

        negl = bm.faces.layers.int.get('neg')
        posl = bm.faces.layers.int.get('pos')

        for key, value in face_info.items():
            # probably a bug, some extra faces which do not belong to any block
            if not value['neg'] and not value['pos']:
                continue
            verts = [bm.verts[v] for v in faces_as_list_of_nodes[key]]
            f = bm.faces.get(verts)
            if not f:
                f = bm.faces.new(verts)
            if value['pos']:
                f[posl] = value['pos'][0]
                dec = sum(x < f[posl] for x in decrease)
                f[posl] -= dec
            else:
                f[posl] = -1
            if value['neg']:
                f[negl] = value['neg'][0]
                dec = sum(x < f[negl] for x in decrease)
                f[negl] -= dec
            else:
                f[negl] = -1

        bpy.ops.object.mode_set(mode='OBJECT')

        edgeDirections = utils.getEdgeDirections(block_verts, block_edges)

        ob = bpy.context.active_object
        me = ob.data
        edgelist = dict()
        for e in me.edges:
            edgelist[(e.vertices[0],e.vertices[1])] = e.index
        for ed in edgeDirections:
            # consistentEdgeDirs(ed)
            for e in ed:
                if (e[0],e[1]) not in edgelist:
                    ei = me.edges[edgelist[(e[1],e[0])]]
                    (e0, e1) = ei.vertices
                    ei.vertices = (e1, e0)
        bpy.ops.object.mode_set(mode='EDIT')

        hideFacesEdges(ob)
        bpy.ops.draw.directions('INVOKE_DEFAULT',show=False)
        self.report({'INFO'}, "Number of blocks: {}".format(len(block_verts)))
        return {"FINISHED"}


# Build the mesh from already existing blocking
def writeMesh(ob, filename = ''):
    if not ob.blocks:
        bpy.ops.build.blocking('INVOKE_DEFAULT')

    verts = list(blender_utils.vertices_from_mesh(ob))


    bm = bmesh.from_edit_mesh(ob.data)
    # do not write polylines for hidden edges
    edges = []
    for e in bm.edges:
        if not e.hide:
            edges.append((e.verts[0].index, e.verts[1].index))

    bpy.ops.object.mode_set(mode='OBJECT')


    ob.select = False
    if ob.Autosnap and ob.EdgeSnapObject:
        polyLines, polyLinesPoints, lengths = getPolyLines(verts, edges, ob)
    else:
        polyLines = []
        lengths = [[]]
    verts = []
    matrix = ob.matrix_world.copy()
    for v in ob.data.vertices:
        verts.append(matrix*v.co)

    blocks = []
    block_names = []
    for b in ob.blocks:
        if b.enabled:
            blocks.append(list(b.verts))
            if b.namedRegion:
                block_names.append(b.name)
            else:
                block_names.append('')

    edgeInfo = collectEdges(ob,lengths)

    bm = bmesh.from_edit_mesh(ob.data)
    detemp = []
    groupl = bm.edges.layers.int.get('groupid')
    ngroups = 0
    for e in bm.edges:
        detemp.append((e[groupl],e.verts[0].index,e.verts[1].index))
        ngroups = max(ngroups,e[groupl])

    block_edges = [[] for i in range(ngroups+1)]
    for e in detemp:
        block_edges[e[0]].append([e[1],e[2]])

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    projections = {'vert':dict(),'edge':dict(),'face':dict()}
    for p in ob.projections:
        if p.type == 'vert' and not bm.verts[p.id].hide:
            key = bm.verts[p.id].index
            if key in projections[p.type]:
                projections[p.type][key] += " {}".format(p.ob)
            else:
                projections[p.type][key] = p.ob
        elif p.type == 'edge' and not bm.edges[p.id].hide:
            key = tuple(v.index for v in bm.edges[p.id].verts)
            if key in projections[p.type]:
                projections[p.type][key] += " {}".format(p.ob)
            else:
                projections[p.type][key] = p.ob
        elif p.type == 'face' and not bm.faces[p.id].hide:
            key = tuple(v.index for v in bm.faces[p.id].verts)
            projections[p.type][key] = p.ob

    selected_edges = [e.select for e in ob.data.edges]

    patchnames = list()
    patchtypes = list()
    patchverts = list()
    patches = list()
    bpy.ops.object.mode_set(mode='EDIT')
    for mid, m in enumerate(ob.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        ob.active_material_index = mid
        bpy.ops.object.material_slot_select()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        faces = ob.data.polygons
        for f in faces:
            if f.select and f.material_index == mid:
                if m.name in patchnames:
                    ind = patchnames.index(m.name)
                    patchverts[ind].append(list(f.vertices))
                else:
                    patchnames.append(m.name)
                    patchtypes.append(m['patchtype'])
                    patchverts.append([list(f.vertices)])

    for ind,pt in enumerate(patchtypes):
        patches.append([pt])
        patches[ind].append(patchnames[ind])
        patches[ind].append(patchverts[ind])

# return edge selection
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for e,sel in zip(ob.data.edges,selected_edges):
        e.select = sel

### This is everything that is related to blockMesh so a new multiblock mesher could be introduced easily just by creating new preview file ###
    if ob.Mesher == 'blockMeshMG':
        from . import blockMeshMG
        importlib.reload(blockMeshMG)
        if filename:
            mesh = blockMeshMG.PreviewMesh(filename)
        else:
            mesh = blockMeshMG.PreviewMesh()
        # projection_tris = writeProjectionObjects(project_verts,project_edges,project_faces, mesh.geomPath)
        geos = writeProjectionObjects(ob, mesh.geomPath)
        projections['geo'] = geos
        cells = mesh.writeBlockMeshDict(verts, 1, patches, polyLines, edgeInfo, block_names, blocks, block_edges, projections)
        # cells = mesh.writeBlockMeshDict(verts, 1, patches, polyLines, edgeInfo, block_names, blocks, block_edges, projection_geos, project_verts, project_edges, project_faces)
###############################################################
    elif ob.Mesher == 'blockMeshBodyFit':
        from . import blockMeshBodyFit
        importlib.reload(blockMeshBodyFit)
        if filename:
            mesh = blockMeshBodyFit.PreviewMesh(filename)
        else:
            mesh = blockMeshBodyFit.PreviewMesh()
        writeProjectionObjects(ob, mesh.triSurfacePath, onlyFaces = True)
        cells = mesh.writeBlockMeshDict(verts, 1, patches, polyLines, edgeInfo, block_names, blocks, block_edges, projections, ob.SearchLength)
    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,True,False)")
    return mesh, cells

class PreviewMesh(bpy.types.Operator):
    bl_idname = "preview.mesh"
    bl_label = "Preview mesh"
    bl_options = {"UNDO"}

    filename = bpy.props.StringProperty(default='')

    def invoke(self, context, event):
        ob = context.active_object
        mesh, cells = writeMesh(ob)
        points, faces = mesh.runMesh()
        blender_utils.previewMesh(ob, points, faces)
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}

class WriteMesh(bpy.types.Operator):
    bl_idname = "write.mesh"
    bl_label = "Write Mesh"

    filepath = bpy.props.StringProperty(
            name="File Path",
            description="Filepath used for exporting the file",
            maxlen=1024,
            subtype='FILE_PATH',
            default='/opt',
            )
    check_existing = bpy.props.BoolProperty(
            name="Check Existing",
            description="Check and warn on overwriting existing files",
            default=True,
            options={'HIDDEN'},
            )
    def invoke(self, context, event):
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        ob = context.active_object
        mesh, cells = writeMesh(ob, self.filepath)
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}

class ActivateBlocking(bpy.types.Operator):
    bl_idname = "activate.blocking"
    bl_label = "Activate blocking"
    bl_options = {"UNDO"}

    hide = bpy.props.BoolProperty()

    def invoke(self, context, event):
        scn = context.scene
        ob = context.active_object
        bob = bpy.data.objects[ob.blocking_object]
        blender_utils.activateObject(bob, self.hide)
        return {'FINISHED'}

class GetBlock(bpy.types.Operator):
    "Get block from selection"
    bl_idname = "get.block"
    bl_label = "Get block"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        selection = []
        for v in bm.verts:
            if v.select:
                selection.append(v.index)
        block = False
        occs = []
        for b in ob.blocks:
            occ = [v in selection for v in b.verts].count(True)
            if occ == 8:
                block = b
                break
            else:
                occs.append(occ)
        if not block:
            max_occ = max(enumerate(occs), key=lambda x:x[1])[0]
            block = ob.blocks[max_occ]
        if not block:
            self.report({'INFO'}, "No block found with selected vertices")
            return {'CANCELLED'}
        bpy.ops.edit.block('INVOKE_DEFAULT', blockid=block.id, name = block.name )
        return {'FINISHED'}

class EditBlock(bpy.types.Operator):
    bl_idname = "edit.block"
    bl_label = "Edit block"
    bl_options = {'REGISTER', 'UNDO'}


    blockid = bpy.props.IntProperty(name='id')
    namedRegion = bpy.props.BoolProperty(name='Named region', default = False)
    name = bpy.props.StringProperty(name='name')

    def draw(self, context):
        ob = context.active_object
        if not ob.blocks[self.blockid].enabled:
            return
        col = self.layout.column(align = True)
        # col.prop(self, "enabled")
        # split = col.split(percentage=0.1, align=True)
        # col = split.column()
        col.prop(self, "namedRegion")
        if self.namedRegion:
            # col = split.column()
            col.prop(self, "name")

# this could be used to select multiple blocks
    def invoke(self, context, event):
        ob = context.active_object
        ob.block_index = self.blockid
        if event.shift:
            self.shiftDown = True
        else:
            self.shiftDown = False
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action="DESELECT")
        scn = context.scene
        ob = context.active_object
        ob.blocks[self.blockid].name = self.name
        ob.blocks[self.blockid].namedRegion = self.namedRegion
        ob = context.active_object

        verts = ob.blocks[self.blockid].verts

        bm = bmesh.from_edit_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        for v in verts:
            bm.verts[v].select = True
        for e in bm.edges:
            if e.verts[0].select and e.verts[1].select:
                e.select = True
        for f in bm.faces:
            if len(f.verts) == 4 and sum([v.select for v in f.verts]) == 4:
                f.select = True
        ob.data.update()
        return {'FINISHED'}

class EnableBlock(bpy.types.Operator):
    bl_idname = "enable.block"
    bl_label = "Enable/disable block"

    blockid = bpy.props.IntProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        block = ob.blocks[self.blockid]
        ob.block_index = self.blockid

        if block.enabled:
            block.enabled = False
        else:
            block.enabled = True
        # repair_blockFacesEdges(ob)
        hideFacesEdges(ob)

        return {'FINISHED'}

# Mapping operators

# Change the layer properties of currently selected edges
class SetEdge(bpy.types.Operator):
    "Set mapping for the edge"
    bl_idname = "set.edgemapping"
    bl_label = "Set edge"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        cellsl = bm.edges.layers.int.get('cells')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        rl = bm.edges.layers.float.get('ratio')
        groupl = bm.edges.layers.int.get('groupid')
        timel = bm.edges.layers.int.get('modtime')

        for e in bm.edges:
            if e.select:
                e[typel] = str.encode(ob.MappingType)
                e[cellsl] = ob.Cells
                e[timel] = time.time()
                if ob.MappingType == "Geometric MG":
                    e[x1l] = ob.x1
                    e[x2l] = ob.x2
                    e[r1l] = ob.r1
                    e[r2l] = ob.r2
                elif ob.MappingType == "Geometric":
                    e[rl] = ob.Ratio
        return {'FINISHED'}

class GetEdge(bpy.types.Operator):
    bl_idname = "get.edge"
    bl_label = "Get edge"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        cellsl = bm.edges.layers.int.get('cells')

        for e in bm.edges:
            if e.select:
                # e[typel] = str.encode(ob.MappingType)
                 ob.Cells = e[cellsl]
                 ob.x1 = e[x1l]
                 ob.x2 = e[x2l]
                 ob.r1 = e[r1l]
                 ob.r2 = e[r2l]
        return {'FINISHED'}

def setCellSize(self, context):
    ob = context.active_object
    scn = context.scene

    bm = bmesh.from_edit_mesh(ob.data)
    typel = bm.edges.layers.string.get('type')
    x1l = bm.edges.layers.float.get('x1')
    x2l = bm.edges.layers.float.get('x2')
    r1l = bm.edges.layers.float.get('r1')
    r2l = bm.edges.layers.float.get('r2')
    cellsl = bm.edges.layers.int.get('cells')

    for e in bm.edges:
        if e.select:
            e[typel] = str.encode(ob.MappingType)
            L = (e.verts[0].co-e.verts[1].co).length
            N=utils.getNodes(ob.x1,ob.x2,ob.r1,ob.r2,L,ob.Dx)
            e[cellsl] = N
            e[x1l] = ob.x1
            e[x2l] = ob.x2
            e[r1l] = ob.r1
            e[r2l] = ob.r2

class EdgeSelectParallel(bpy.types.Operator):
    bl_idname = "select.parallel"
    bl_label = "Select parallel edges"

    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        for e in bm.edges:
            if e.select:
                groupid = e[groupl]
                for i in bm.edges:
                    if i[groupl] == groupid:
                        i.select = True
        ob.data.update()
        return {'FINISHED'}

class FlipEdges(bpy.types.Operator):
    "Flips parallel edges, select only one edge per group"
    bl_idname = "flip.edges"
    bl_label = "Flip edges"

    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        flip_edges = []
        for e in bm.edges:
            if e.select:
                groupid = e[groupl]
                for i in bm.edges:
                    if i[groupl] == groupid:
                        flip_edges.append(i.index)
                break
        bpy.ops.object.mode_set(mode='OBJECT')
        for fe in flip_edges:
            e = ob.data.edges[fe]
            (e0,e1) = e.vertices
            e.vertices = (e1,e0)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.draw.directions('INVOKE_DEFAULT',show=False)
        return {'FINISHED'}

def collectEdges(bob, lengths):
    bob.select = True
    bpy.context.scene.objects.active = bob
    bpy.ops.object.mode_set(mode='EDIT')
    # snap_vertices = get_snap_vertices(bob)
    bm = bmesh.from_edit_mesh(bob.data)
    layers = bm.edges.layers
    # snapIdl = layers.string.get('snapId')
    block_edges = dict()

    timel = layers.int.get('modtime')
    groupl = layers.int.get('groupid')
    x1l = layers.float.get('x1')
    x2l = layers.float.get('x2')
    r1l = layers.float.get('r1')
    r2l = layers.float.get('r2')
    cellsl = layers.int.get('cells')
    ratiol = layers.float.get("ratio")

    ncells = dict()
    times = dict()
    for e in bm.edges:
        if e[groupl] not in ncells:
            ncells[e[groupl]] = e[cellsl]
            times[e[groupl]] = e[timel]
        elif e[timel] > times[e[groupl]]:
            ncells[e[groupl]] = e[cellsl]
            times[e[groupl]] = e[timel]

    for e in bm.edges:
        be = dict()
        ev = list([e.verts[0].index,e.verts[1].index])
        if ev in lengths[0]:
            ind = lengths[0].index(ev)
            L = lengths[1][ind]
        else:
            L = (e.verts[0].co-e.verts[1].co).length
        be["type"] = bob.MappingType
        be["x1"] = e[x1l] 
        be["x2"] = e[x2l] 
        be["r1"] = e[r1l] 
        be["r2"] = e[r2l] 
        be["N"] = ncells[e[groupl]]
        be["ratio"] = e[ratiol]
        be["L"] = L
        if not be["N"]:
            be["N"] = 10
        if not be["r1"]:
            be["r1"] = 1.
        if not be["r2"]:
            be["r2"] = 1.
        if not be["ratio"]:
            be["ratio"] = 1
        be = utils.edgeMapping(be)
        block_edges[(e.verts[1].index,e.verts[0].index)] = be
        be = dict(be)
        be["x1"],be["x2"] = be["x2"],be["x1"]
        be["r1"],be["r2"] = be["r2"],be["r1"]
        be["ratio"] = 1./be["ratio"]
        be = utils.edgeMapping(be)

        block_edges[(e.verts[0].index,e.verts[1].index)] = be
    return block_edges

# Projection operators

class GetProjection(bpy.types.Operator):
    bl_idname = "get.projection"
    bl_label = "Get projection"

    id = bpy.props.IntProperty()
    type = bpy.props.StringProperty()

    def invoke(self, context, event):
        if not event.shift:
            bpy.ops.mesh.select_all(action='DESELECT')
        self.execute(context)
        return {'FINISHED'}


    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        if self.type == 'vert':
            bm.verts.ensure_lookup_table()
            bm.verts[self.id].select = True
        elif self.type == 'edge':
            bm.edges[self.id].select = True
        elif self.type == 'face':
            bm.faces[self.id].select = True
        ob.data.update()
        return {'FINISHED'}

class AddProjections(bpy.types.Operator):
    bl_idname = "add.projections"
    bl_label = "Project to surface"
    bl_options = {"REGISTER","UNDO"}

    pob = bpy.props.EnumProperty(name="Projection object",
            items=getProjectionObjects, description = "Projection object")

    verts = bpy.props.BoolProperty(default=True)
    edges = bpy.props.BoolProperty(default=True)
    faces = bpy.props.BoolProperty(default=True)

    def invoke(self, context, event):
        self.added = 1
        return self.execute(context)

    def execute(self, context):
        def projectionExists(ob, ptype, index, pob):
            for p in ob.projections:
                if p.type == ptype and p.id == index and p.ob == pob:
                    return True
            return False
        def addProjection(ptype, index):
            for p in ob.projections:
                if p.type == ptype and p.id == index and p.ob == self.pob:
                    return
            newp = ob.projections.add()
            newp.type = ptype
            newp.id = index
            newp.ob = self.pob
            self.added += 1

        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        if not self.pob:
            return {"CANCELLED"}

        np = len(ob.projections)
        for i in range(self.added):
            ob.projections.remove(np-i)

        for v in bm.verts:
            if v.select and self.verts:
                addProjection('vert', v.index)

        for e in bm.edges:
            if e.select and self.edges:
                addProjection('edge', e.index)

        for f in bm.faces:
            if f.select and self.faces:
                addProjection('face', f.index)
        return {"FINISHED"}

class RemoveProjection(bpy.types.Operator):
    bl_idname = "remove.projection"
    bl_label = "Remove projection"
    bl_options = {"UNDO"}

    proj_id = bpy.props.IntProperty(default = -1)

    def execute(self, context):
        ob = context.active_object
        print('removed',self.proj_id)
        if self.proj_id != -1:
            ob.projections.remove(self.proj_id)
        return {"FINISHED"}

class RemoveProjections(bpy.types.Operator):
    bl_idname = "remove.projections"
    bl_label = "Remove projections"
    bl_options = {"UNDO"}


    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        remove_projections = []

        for v in bm.verts:
            if v.select:
                for i,p in enumerate(ob.projections):
                    if p.type == 'vert' and p.id == v.index:
                        remove_projections.append(i)
        for e in bm.edges:
            if e.select:
                for i,p in enumerate(ob.projections):
                    if p.type == 'edge' and p.id == e.index:
                        remove_projections.append(i)
        for f in bm.faces:
            if f.select:
                for i,p in enumerate(ob.projections):
                    if p.type == 'face' and p.id == f.index:
                        remove_projections.append(i)
        remove_projections = reversed(sorted(remove_projections))
        for i in remove_projections:
            ob.projections.remove(i)
        return {"FINISHED"}

def writeProjectionObjects(ob, path, onlyFaces = True):
    objects = []
    for p in ob.projections:
        if onlyFaces and not p.type == 'face':
            continue
        else:
            objects.append(p.ob)
    objects = set(objects)
    for o in objects:
        sob = bpy.data.objects[o]
        blender_utils.activateObject(sob)
        bpy.ops.export_mesh.stl('EXEC_DEFAULT',filepath = path + '/{}.stl'.format(o))
    blender_utils.activateObject(ob,True)
    return objects

class ActivateSnap(bpy.types.Operator):
    bl_idname = "activate.object"
    bl_label = "Activate snapping object"
    bl_options = {"UNDO"}

    ob = bpy.props.StringProperty()


    def invoke(self, context, event):
        scn = context.scene
        ob = context.active_object
        pob = bpy.data.objects[self.ob]
        pob.blocking_object = ob.name
        blender_utils.activateObject(pob, False)
        return {'FINISHED'}

# Boundary condition operators
def patchColor(patch_no):
    color = [(0.25,0.25,0.25), (1.0,0.,0.), (0.0,1.,0.),(0.0,0.,1.),(0.707,0.707,0),(0,0.707,0.707),(0.707,0,0.707)]
    return color[patch_no % len(color)]

class OBJECT_OT_SetPatchName(bpy.types.Operator):
    '''Set the given name to the selected faces'''
    bl_idname = "set.patchname"
    bl_label = "Set name"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        NoSelected = 0
        for f in ob.data.polygons:
            if f.select:
                NoSelected += 1
        if NoSelected:
            namestr = ob.patchName
            namestr = namestr.strip()
            namestr = namestr.replace(' ', '_')
            try:
                mat = bpy.data.materials[namestr]
                patchindex = list(ob.data.materials).index(mat)
                ob.active_material_index = patchindex
            except: # add a new patchname (as a blender material, as such face props are conserved during mesh mods)
                mat = bpy.data.materials.new(namestr)
                mat.diffuse_color = patchColor(len(ob.data.materials))
                bpy.ops.object.material_slot_add()
                ob.material_slots[-1].material = mat
            mat['patchtype'] = ob.bcTypeEnum
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.material_slot_assign()
        else:
            self.report({'INFO'}, "No faces selected!")
            return{'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_GetPatch(bpy.types.Operator):
    '''Click to select faces belonging to this patch'''
    bl_idname = "set.getpatch"
    bl_label = "Get patch"

    whichPatch = bpy.props.StringProperty()
    shiftDown = False

    def invoke(self, context, event):
        if event.shift:
            self.shiftDown = True
        else:
            self.shiftDown = False
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
        if not self.shiftDown:
            bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mat = bpy.data.materials[self.whichPatch]
        patchindex = list(ob.data.materials).index(mat)
        ob.active_material_index = patchindex
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_select()
        ob.bcTypeEnum = mat['patchtype']
        ob.patchName = self.whichPatch
        return {'FINISHED'}

# Edge group operators
class RemoveEdgeGroup(bpy.types.Operator):
    bl_idname = "remove.edgegroup"
    bl_label = "Remove edge group"
    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        for i,eg in enumerate(ob.edge_groups):
            if eg.group_name == self.egName:
                ob.edge_groups.remove(i)
                return {'FINISHED'}
        return {'CANCEL'}

class GetEdgeGroup(bpy.types.Operator):
    bl_idname = "get.edgegroup"
    bl_label = "Get edge group"

    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.mesh.select_all(action="DESELECT")

        bm = bmesh.from_edit_mesh(ob.data)
        for eg in ob.edge_groups:
            if eg.group_name == self.egName:
                edges = list(map(int,eg.group_edges.split(',')))
                for e in edges:
                    bm.edges[e].select = True
        ob.data.update()
        return {'FINISHED'}


class AddEdgeGroup(bpy.types.Operator):
    '''Set the given name to the selected edges'''
    bl_idname = "add.edgegroup"
    bl_label = "Add edge group"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        ob.data.update()
        edges = []
        for e in ob.data.edges:
            if e.select:
                edges.append(e.index)
        edgesstr = ','.join(map(str,edges))
        for e in ob.edge_groups:
            if e.group_name == ob.EdgeGroupName:
                e.group_edges = edgesstr
                return {'FINISHED'}
        eg = ob.edge_groups.add()
        eg.group_name = ob.EdgeGroupName
        eg.group_edges = edgesstr
        return {'FINISHED'}

# Other stuff
class BlockExtrusion(bpy.types.Operator):
    "Extrude blocks without removing internal edges"
    bl_idname = "extrude.blocks"
    bl_label = "Extrude blocks"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.extrude_faces_move()
        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False)
        bpy.ops.transform.translate('INVOKE_REGION_WIN')
        return {"FINISHED"}

def blockExtrusion_menu(self, context):
    self.layout.operator("extrude.blocks")

def changeMesher(self, context):
    ob = context.active_object
    if ob.Mesher == "blockMeshMG":
        ob.MappingType = "Geometric MG"
    elif ob.Mesher == "blockMeshBodyFit":
        ob.MappingType = "Geometric"

class DrawEdgeDirections(bpy.types.Operator):
    "Draw edge directions"
    bl_idname = "draw.directions"
    bl_label = "draw edge directions"
    bl_options = {'REGISTER', 'UNDO'}

    show = bpy.props.BoolProperty(default=True)
    size = bpy.props.FloatProperty(default=0,min=0)
    verts = bpy.props.IntProperty(default=12,min=0)
    relativeSize = bpy.props.BoolProperty(default=True)

    def invoke(self, context, event):
        self.bob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(self.bob.data)
        self.edges = []
        for e in bm.edges:
            if not e.hide:
                self.edges.append((Vector(e.verts[0].co[:]),Vector(e.verts[1].co[:])))
        self.lengths = [(e[0]-e[1]).length for e in self.edges]
        self.size = 0.1
        self.execute(context)
        return {"FINISHED"}


    def execute(self,context):
        try:
            eob = bpy.data.objects['Edge_directions']
            self.remove(context,eob)
        except:
            pass
        if not self.edges or not self.show:
            self.bob.direction_object = ''
            return {"CANCELLED"}
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.mesh.primitive_cone_add(vertices=self.verts,radius1=0.3,depth=1)#,end_fill_type='NOTHING')
        default_arrow = context.active_object
        arrows = []
        # this is "a bit" slow
        for e,l in zip(self.edges,self.lengths):
            v1 = Vector(e[0])
            v2 = Vector(e[1])
            tob = bpy.data.objects.new("Arrow_duplicate", default_arrow.data)
            tob.location = v1+0.5*(v2-v1)
            if self.relativeSize:
                scale = self.size*l
            else:
                scale = self.size
            tob.scale = (scale,scale,scale)
            tob.rotation_mode = 'QUATERNION'
            tob.rotation_quaternion = (v1-v2).to_track_quat('Z','Y')
            context.scene.objects.link(tob)
            arrows.append(tob)
            tob.select = True
        aob = arrows[0]
        bpy.context.scene.objects.active = aob
        aob.name = 'Edge_directions'
        aob.hide_select = True

        mat = bpy.data.materials.new('black')
        mat.emit = 2
        mat.diffuse_color = (0,0,0)
        bpy.ops.object.material_slot_add()
        aob.material_slots[-1].material = mat
        self.remove(context, default_arrow)
        aob.isdirectionObject = True

        bpy.ops.object.join()
        bpy.ops.object.shade_smooth()
        blender_utils.activateObject(self.bob)
        self.bob.direction_object = aob.name
        return {"FINISHED"}

    def remove(self, context, ob):
        context.scene.objects.unlink(ob)
        bpy.data.objects.remove(ob)

def hideFacesEdges(ob):
    ob.data.update()
    bm = bmesh.from_edit_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    negl = bm.faces.layers.int.get('neg')
    posl = bm.faces.layers.int.get('pos')

    for f in bm.faces:
        if f[negl] != -1 and f[posl] != -1: #internal face
            if (not ob.blocks[f[posl]].enabled and ob.blocks[f[negl]].enabled) \
                    or (ob.blocks[f[posl]].enabled and not ob.blocks[f[negl]].enabled):
                f.hide_set(False)# = False
            else:
                # f.hide_set(True)# = True
                f.hide = True
        elif (f[posl] == -1 and f[negl] != -1): #boundary face
            if ob.blocks[f[negl]].enabled:
                f.hide_set(False)# = False
            else:
                f.hide_set(True)# = True
        elif (f[posl] != -1 and f[negl] == -1): #boundary face
            if ob.blocks[f[posl]].enabled:
                f.hide_set(False)
            else:
                f.hide_set(True)

    for e in bm.edges:
        edge_found = False
        for b in ob.blocks:
            if b.enabled and e.verts[0].index in b.verts and e.verts[1].index in b.verts:
                edge_found = True
                e.hide = False
                continue
        if not edge_found:
            e.hide_set(True)

    bpy.ops.draw.directions('INVOKE_DEFAULT',show=False)
    ob.data.update()



# Kalle's implementation
def getPolyLines(verts, edges, bob):
    scn = bpy.context.scene
    polyLinesPoints = []
    polyLines = ''
    polyLinesLengths = [[], []]
    tol = 1e-6

    def isPointOnEdge(point, A, B):
        eps = (((A - B).magnitude - (point-B).magnitude) - (A-point).magnitude)
        return True if (abs(eps) < tol) else False

    # nosnap= [False for i in range(len(edges))]
    # for eid, e in enumerate(obj.data.edges):
        # nosnap[eid] = e.use_edge_sharp

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    geoobj = bpy.data.objects[bob.EdgeSnapObject]
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    geoobj.select = False # avoid deletion

# First go through all vertices in the block structure and find vertices snapped to edges
# When found, add a vertex at that location to the polyLine object by splitting the edge
# Create a new Blender object containing the newly inserted verts. Then use Blender's
# shortest path algo to find polyLines.

    for vid, v in enumerate(verts):
        found = False
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                found = True
                break   # We have found a vertex co-located, continue with next block vertex
        if not found:
            for geid, ge in enumerate(geo_edges):
                if (isPointOnEdge(v, geo_verts[ge[0]], geo_verts[ge[1]])):
                    geo_verts.append(v)
                    geo_edges.append([geo_edges[geid][1],len(geo_verts)-1]) # Putting the vert on the edge, by splitting it in two.
                    geo_edges[geid][1] = len(geo_verts)-1
                    break # No more iteration, go to next block vertex

    mesh_data = bpy.data.meshes.new("deleteme")
    mesh_data.from_pydata(geo_verts, geo_edges, [])
    mesh_data.update()
    geoobj = bpy.data.objects.new('deleteme', mesh_data)
    bpy.context.scene.objects.link(geoobj)
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    bpy.context.scene.objects.active=geoobj

# Now start the search over again on the new object with more verts
    snapped_verts = {}
    for vid, v in enumerate(verts):
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                snapped_verts[vid] = gvid
                break   # We have found a vertex co-located, continue with next block vertex

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    for edid, ed in enumerate(edges):
        if ed[0] in snapped_verts and ed[1] in snapped_verts:# and not nosnap[edid]:
            geoobj.hide = False
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            geoobj.data.vertices[snapped_verts[ed[0]]].select = True
            geoobj.data.vertices[snapped_verts[ed[1]]].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_vertex_path(type='EDGE_LENGTH')
            except:
                bpy.ops.mesh.shortest_path_select()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.duplicate()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            polyLineobj = bpy.data.objects['deleteme.001']
            if len(polyLineobj.data.vertices) > 2:
                polyLineverts = list(blender_utils.vertices_from_mesh(polyLineobj))
                polyLineedges = list(blender_utils.edges_from_mesh(polyLineobj))
                for vid, v in enumerate(polyLineverts):
                    mag = (v-verts[ed[0]]).magnitude
                    if mag < tol:
                        startVertex = vid
                        break
                polyLineStr, vectors, length = sortedVertices(polyLineverts,polyLineedges,startVertex)
                polyLinesPoints.append([ed[0],ed[1],vectors])
                polyLinesLengths[0].append([min(ed[0],ed[1]), max(ed[0],ed[1])]) # write out sorted
                polyLinesLengths[1].append(length)
                polyLine = 'polyLine {} {} ('.format(*ed)
                polyLine += polyLineStr
                polyLine += ')\n'
                polyLines += polyLine

            geoobj.select = False
            polyLineobj.select = True
            bpy.ops.object.delete()
    geoobj.select = True
    bpy.ops.object.delete()
    return polyLines, polyLinesPoints, polyLinesLengths

def sortedVertices(verts,edges,startVert):
    sorted = []
    vectors = []
    sorted.append(startVert)
    vert = startVert
    length = len(edges)+1
    for i in range(len(verts)):
        for eid, e in enumerate(edges):
            if vert in e:
                if e[0] == vert:
                    sorted.append(e[1])
                else:
                    sorted.append(e[0])
                edges.pop(eid)
                vert = sorted[-1]
                break

    polyLine = ''
    length = 0.
    for vid, v in enumerate(sorted):
        polyLine += '({} {} {})'.format(*verts[v])
        vectors.append(verts[v])
        if vid>=1:
            length += (vectors[vid] - vectors[vid-1]).magnitude
    return polyLine, vectors, length

initSwiftBlockProperties()

def register():
    bpy.utils.register_module(__name__)
    bpy.types.VIEW3D_MT_edit_mesh_extrude.prepend(blockExtrusion_menu)
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.VIEW3D_MT_edit_mesh_extrude.remove(blockExtrusion_menu)
if __name__ == "__main__":
    register()
