bl_info = {
    "name": "SwiftBlock",
    "author": "Karl-Johan Nogenmyr, Mikko Folkersma, Turo Välikangas",
    "version": (0, 1),
    "blender": (2, 7, 8),
    "api": 44000,
    "location": "Tool Shelf",
    "description": "Writes block geometry as blockMeshDict file",
    "warning": "not much tested yet",
    "wiki_url": "http://openfoamwiki.net/index.php/SwiftBlock",
    "tracker_url": "",
    "support": 'COMMUNITY',
    "category": "OpenFOAM"}

#----------------------------------------------------------
# File scene_props.py
#----------------------------------------------------------
import bpy
from bpy.props import *
import bmesh
import time
from math import fabs, degrees, radians, sqrt, cos, sin, pi
from mathutils import Vector, Matrix


#Here will be the coloring definitions
def shortenedVector(p1,p2,length):
    v = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    vlen= sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])
    vn= (v[0]/vlen,v[1]/vlen,v[2]/vlen )
    l=length
    return length,(p1[0]+l*vn[0], p1[1]+l*vn[1],p1[2]+l*vn[2])


def createLine(lineName, pointList, thickness,length,blType):
    sVLength,sV = shortenedVector(pointList[0],pointList[1],length)
    # setup basic line data
    theLineData = bpy.data.curves.new(name=lineName,type='CURVE')
    theLineData.dimensions = '3D'
    theLineData.fill_mode = 'FULL'
    theLineData.bevel_depth = 0.1*sVLength*(thickness*thickness)
    # define points that make the line
    polyline = theLineData.splines.new('POLY')
    polyline.points.add(len(pointList)-1)
    for idx in range(len(pointList)):
        polyline.points[idx].co = (pointList[idx])+(1.0,)
    polyline.points[0].co = (pointList[0])+(1.0,)
    polyline.points[1].co = (sV)+(1.0,)

    # create an object that uses the linedata
    theLine = bpy.data.objects.new('blflags',theLineData)
    bpy.context.scene.objects.link(theLine)
    theLine.location = (0.0,0.0,0.0)
    
    # setup a material
    lmat = bpy.data.materials.new('Linematerial')
    if blType == "bl1":
        lmat.diffuse_color = (0.0,0.0,1.0)
    if blType == "bl2":
        lmat.diffuse_color = (1.0,0.0,0.0)
    lmat.use_shadeless = True
    theLine.data.materials.append(lmat)

####And coloring ends here


def getPolyLines(verts, edges, obj):
    scn = bpy.context.scene
    polyLinesPoints = []
    polyLines = ''
    polyLinesLengths = [[], []]

    def isPointOnEdge(point, A, B):
        eps = (((A - B).magnitude - (point-B).magnitude) - (A-point).magnitude)
        return True if (abs(eps) < scn.tol) else False

    nosnap= [False for i in range(len(edges))]
    for eid, e in enumerate(obj.data.edges):
        nosnap[eid] = e.use_edge_sharp

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    geoobj = bpy.data.objects[scn.geoobjName]
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
            if mag < scn.tol:
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
            if mag < scn.tol:
                snapped_verts[vid] = gvid
                break   # We have found a vertex co-located, continue with next block vertex

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    for edid, ed in enumerate(edges):
        if ed[0] in snapped_verts and ed[1] in snapped_verts and not nosnap[edid]:
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
                    if mag < scn.tol:
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

def patchColor(patch_no):
    color = [(1.0,0.,0.), (0.0,1.,0.),(0.0,0.,1.),(0.707,0.707,0),(0,0.707,0.707),(0.707,0,0.707)]
    return color[patch_no % len(color)]

def initProperties():

    bpy.types.Scene.tol = FloatProperty(
        name = "tol",
        description = "Snapping tolerance",
        default = 1e-6,
        min = 0.)

    bpy.types.Scene.ctmFloat = FloatProperty(
        name = "convertToMeters",
        description = "Conversion factor: Blender coords to meter",
        default = 1.0,
        min = 0.)


    bpy.types.Scene.whichCell = EnumProperty(
        items = [('Coarse', 'Coarse', 'Let the coarse cells have the target resolution'),
                 ('Fine', 'Fine', 'Let the fine cells have the target resolution')
                 ],
        name = "Cell resolution")

    bpy.types.Scene.setEdges = BoolProperty(
        name = "Set edges",
        description = "Should edges be fetched from another object?",
        default = False)

    bpy.types.Scene.setGlobalMax = BoolProperty(
        name = "Set global max",
        description = "Do you want to set a global maximum cell size.",
        default = False)

    bpy.types.Scene.setBoundaryLayer = BoolProperty(
        name = "Set global boundary layer settings",
        description = "Do you want to set dx and exp for all boundary layer edges?",
        default = False)

    bpy.types.Scene.setInitBL = BoolProperty(
        name = "Initialise boundary layer",
        description = "If boundary layers give you an error, try to initialize them?",
        default = False)
    
    bpy.types.Scene.DeleteBL = BoolProperty(
        name = "Delete boundary layer flags",
        description = "If you want to hide all the boundary layer flags press this.",
        default = False)
    
    bpy.types.Scene.globalMax = FloatProperty(
        name = "global max",
        description = "Global maximum cell size.",
        default = 1,
        min = 1e-6)

    bpy.types.Scene.bldx1 = FloatProperty(
        name = "dx when bl=1",
        description = "Global boundary layer cell size at start of edge.",
        default = 1,
        min = 1e-6)
 
    bpy.types.Scene.blexp1= FloatProperty(
        name = "exp when bl=1",
        description = "Global boundary layer expansion ratio at start of edge.",
        default = 1,
        min = 1e-6)

    bpy.types.Scene.bldx2 = FloatProperty(
        name = "dx when bl=2",
        description = "Global boundary layer cell size at end of edge.",
        default = 1,
        min = 1e-6)
 
    bpy.types.Scene.blexp2 = FloatProperty(
        name = "exp when bl=2",
        description = "Global boundary layer expansion ratio at end of edge.",
        default = 1,
        min = 1e-6)


    bpy.types.Scene.geoobjName = StringProperty(
        name = "Object",
        description = "Name of object to get edges from (this box disappears when object is found)",
        default = '')

    bpy.types.Scene.bcTypeEnum = EnumProperty(
        items = [('wall', 'wall', 'Defines the patch as wall'),
                 ('patch', 'patch', 'Defines the patch as generic patch'),
                 ('empty', 'empty', 'Defines the patch as empty'),
                 ('symmetryPlane', 'symmetryPlane', 'Defines the patch as symmetryPlane'),
                 ],
        name = "Patch type")

    bpy.types.Scene.patchName = StringProperty(
        name = "Patch name",
        description = "Specify name of patch (max 31 chars)",
        default = "defaultName")

    bpy.types.Scene.snapping = EnumProperty(
        items = [('yes', 'Yes', 'The edge gets a polyLine if its vertices are snapped'),
                 ('no', 'No', 'The edge will be meshed as a straight line')
                 ],
        name = "Edge snapping")

    bpy.types.Scene.removeInternal = BoolProperty(
        name = "Remove internal faces",
        description = "Should internal faces be removed?",
        default = False)

    bpy.types.Scene.createBoundary = BoolProperty(
        name = "Create boundary faces",
        description = "Should boundary faces be created?",
        default = False)

    bpy.types.Scene.dx1 = FloatProperty(
        name = "dx1",
        description = "First cell size on first end",
        default = 0,
        min = 0)

    bpy.types.Scene.dx2 = FloatProperty(
        name = "dx2",
        description = "First cell size on second end",
        default = 0,
        min = 0)

    bpy.types.Scene.exp1 = FloatProperty(
        name = "exp1",
        description = "Expansion ratio on first end",
        default = 1,
        min = 1)

    bpy.types.Scene.exp2 = FloatProperty(
        name = "exp2",
        description = "Expansion ratio on second end",
        default = 1,
        min = 1)

    bpy.types.Scene.bl1 = IntProperty(
        name = "bl1",
        description = "Do you want to define global boundary layers? 1,2=define global rules, 3=global settings does not apply and 0=no",
        default = 0,
        min = 0)

    bpy.types.Scene.bl2 = IntProperty(
        name = "bl2",
        description = "Do you want to define global boundary layers? 1,2=define global rules, 3=global settings does not apply and 0=no",
        default = 0,
        min = 0)

    bpy.types.Scene.cells = IntProperty(
        name = "cells",
        description = "Number of cells",
        default = 0,
        min = 0)

    bpy.types.Scene.maxdx = FloatProperty(
        name = "max dx",
        description = "Maximum cell size",
        default = 1,
        min = 1e-6)

    bpy.types.Scene.copyAligned = BoolProperty(
        name = "Copy to parallel edges",
        description = "Copy edge properties to parallel edges",
        default = False)
    return

#
#    Menu in UI region
#
class UIPanel(bpy.types.Panel):
    bl_label = "SwiftBlock settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):

        layout = self.layout
        scn = context.scene
        obj = context.active_object

        try:
            obj['swiftblock']
        except:
            try:
                obj['swiftBlockObj']
                layout.operator("delete.preview")

            except:
                layout.operator("enable.swiftblock")

        else:
            layout = layout.column()
            layout.operator("write.bmdfile")
#            split=layout.split()
#            col = split.column()
            layout.operator("create.preview")
#            col = split.column()
#            col.prop(scn, 'internalCells')
            layout.operator("find.broken")
            layout.operator('build.blocking')
            layout.prop(scn, 'ctmFloat')
#            layout.prop(scn, 'resFloat')
            box = layout.box()
            box = box.column()
            box.label(text='Global variables')

            box.prop(scn,'setGlobalMax')
            if scn.setGlobalMax:
                box.prop(scn,'globalMax')
                box = box.column()
                box.operator('set.globalmax')

            box.prop(scn,'setBoundaryLayer')
            if scn.setBoundaryLayer:
                box.prop(scn,'bldx1')
                box.prop(scn,'blexp1')
                box.prop(scn,'bldx2')
                box.prop(scn,'blexp2')
                box = box.column()
                box.operator('set.boundarylayery')
                box.prop(scn,'setInitBL')
                if scn.setInitBL:
                    box.operator('init.boundarylayer')
                box.prop(scn,'DeleteBL')
                if scn.DeleteBL:
                    box.operator('del.bl')
                

            box = box.column()

            box.label(text='Edge settings')

            box.prop(scn, 'setEdges')
            if scn.setEdges:
                try:
                    geoojb = bpy.data.objects[scn.geoobjName]
                    textstr = "Fetching egde's polyLines from " + geoojb.name
                    box.operator("change.geoobj", text=textstr, emboss=False)
#                    box.prop(scn, 'tol') # the tolerance setting do not behave as I expected... do not adjust for now
                    split = box.split()
                    col = split.column()
                    col.operator('nosnap.edge', text='Curved').snapping = True
                    col = split.column()
                    col.operator('nosnap.edge', text='Straight')
                    box.separator()
                except:
                    box.prop(scn, 'geoobjName')
	    
	    
	
            box = box.column()
            box.label(text='dx= cell size at start/end')
            box.label(text='exp= expansion ratio at start/end')
            split = box.split()
            col = split.column()
            col.label(text='Start of edge')
            col.prop(scn, 'dx1')
            col.prop(scn, 'exp1')
            col.prop(scn, 'bl1')    
            col = split.column()
            col.label(text='End of edge')
            col.prop(scn, 'dx2')
            col.prop(scn, 'exp2')
            col.prop(scn, 'bl2')
#            box.prop(scn, 'cells')
            box.prop(scn, 'maxdx')
		
            box.prop(scn, 'copyAligned')
            split = box.split()
            col = split.column()
            col.operator('set.edges')
            col = split.column()
            col.operator('get.edges')
            box = layout.box()
            box = box.column()
            box.label(text='Patch settings')
            box.prop(scn, 'patchName')
            box.prop(scn, 'bcTypeEnum')
            box.operator("set.patchname")
            for m in obj.data.materials:
                try:
                    patchtype = str(' ' + m['patchtype'])
                    split = box.split(percentage=0.2, align=True)
                    col = split.column()
                    col.prop(m, "diffuse_color", text="")
                    col = split.column()
                    col.operator("set.getpatch", text=m.name + patchtype, emboss=False).whichPatch = m.name
                except:
                    pass
            box.operator("repair.faces")

            group = obj.vertex_groups.active
            rows = 2
            if group:
                rows = 4

            layout.label('Block\'s name settings')
            row = layout.row()
            row.template_list("MESH_UL_vgroups", "", obj, "vertex_groups", obj.vertex_groups, "active_index", rows=rows)
            col = row.column(align=True)
            col.operator("object.vertex_group_add", icon='ZOOMIN', text="")
            col.operator("object.vertex_group_remove", icon='ZOOMOUT', text="").all = False
            if group:
                col.separator()
                col.operator("object.vertex_group_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.vertex_group_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if group:
                row = layout.row()
                row.prop(group, "name")

            if obj.vertex_groups and obj.mode == 'EDIT':
                row = layout.row()

                sub = row.row(align=True)
                sub.operator("object.vertex_group_assign", text="Assign")
                sub.operator("object.vertex_group_remove_from", text="Remove")
                sub = row.row(align=True)
                sub.operator("object.vertex_group_select", text="Select")
                sub.operator("object.vertex_group_deselect", text="Deselect")


class OBJECT_OT_nosnapEdge(bpy.types.Operator):
    '''Force selected edge(s) straight or curved'''
    bl_idname = "nosnap.edge"
    bl_label = "No snap"

    snapping = BoolProperty(default = False)

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        NoSelect = 0
        for e in obj.data.edges:
            if e.select:
                NoSelect += 1
                if not self.snapping:
                    e.use_edge_sharp = True
                else:
                    e.use_edge_sharp = False

        if not NoSelect:
            self.report({'INFO'}, "No edge(s) selected!")
            bpy.ops.object.mode_set(mode='EDIT')
            return{'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        return {'RUNNING_MODAL'}


class OBJECT_OT_insertSmoother(bpy.types.Operator):
    '''Inserts a smoother'''
    bl_idname = "insert.smoother"
    bl_label = "Insert smoother"

    def execute(self, context):
        try:
            bpy.data.objects[context.scene.geoobjName]
        except:
            self.report({'INFO'}, "Cannot find object for edges!")
            return{'CANCELLED'}
        import mathutils
        from . import utils
        bpy.ops.object.mode_set(mode='OBJECT')
        scn = context.scene
        obj = context.active_object
        obj.select=False
        geoobj = bpy.data.objects[scn.geoobjName]
        geoobj.hide = False
        centre = mathutils.Vector((0,0,0))
        no_verts = 0
        profile = utils.smootherProfile()
        res = profile.__len__()
        matrix = obj.matrix_world.copy()
        for v in obj.data.vertices:
            if v.select:
                 centre += matrix*v.co
                 no_verts += 1
        if no_verts == 0:
            self.report({'INFO'}, "Nothing selected!")
            return{'CANCELLED'}

        centre /= no_verts
        if no_verts <= 2:
             centre = mathutils.Vector((0,0,centre[2]))
        for e in obj.data.edges:
            if e.select:
                (v0id, v1id) = e.vertices
                v0 = matrix*obj.data.vertices[v0id].co
                v1 = matrix*obj.data.vertices[v1id].co
                edgevector = v1-v0
                normal = centre-v0
                tang = normal.project(edgevector)
                normal -= tang
                normal.normalize()
                normal *= -edgevector.length
                p = [v0 for i in range(res)]
                e = [[0,1] for i in range(res)]
                for i in range(res):
                    linecoord = float(i)/(res-1)
                    p[i] = (1-linecoord)*v0+linecoord*v1
                    p[i] += 0.05*normal*profile[i]
                for i in range(res-1):
                    e[i] = [i,i+1]
                mesh_data = bpy.data.meshes.new("deleteme")
                mesh_data.from_pydata(p, e, [])
                mesh_data.update()
                addtoobj = bpy.data.objects.new('deleteme', mesh_data)
                bpy.context.scene.objects.link(addtoobj)
                bpy.data.objects['deleteme'].select = True
                geoobj.select = True
                scn.objects.active = geoobj
                bpy.ops.object.join()
                geoobj.select = False

        geoobj.select = True
        scn.objects.active = geoobj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        geoobj.select = False
        obj.select = True
        scn.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class OBJECT_OT_flipEdge(bpy.types.Operator):
    '''Flip direction of selected edge(s). This is useful if you want to \
set grading on several edges which are initially misaligned'''
    bl_idname = "flip.edge"
    bl_label = "Flip edge"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        for e in obj.data.edges:
            if e.select:
                (e0, e1) = e.vertices
                e.vertices = (e1, e0)

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}



class OBJECT_OT_ChangeGeoObj(bpy.types.Operator):
    '''Click to change object'''
    bl_idname = "change.geoobj"
    bl_label = "Change"

    def execute(self, context):
        context.scene.geoobjName = ''
        return {'FINISHED'}

class OBJECT_OT_Enable(bpy.types.Operator):
    '''Enables SwiftBlock for the active object'''
    bl_idname = "enable.swiftblock"
    bl_label = "Enable SwiftBlock"

    def execute(self, context):
        obj = context.active_object
        obj['swiftblock'] = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.edges.layers.float.new("dx1")
        bm.edges.layers.float.new("dx2")
        bm.edges.layers.float.new("exp1")
        bm.edges.layers.float.new("exp2")
        bm.edges.layers.int.new("bl1")
        bm.edges.layers.int.new("bl2")
        bm.edges.layers.float.new("maxdx")
        bm.edges.layers.int.new("cells")
        bm.edges.layers.float.new("time")
        bm.edges.layers.int.new("copyAligned")
        bpy.ops.object.mode_set(mode='OBJECT')
        bm.to_mesh(obj.data)
        bpy.context.tool_settings.use_mesh_automerge = True

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.material_slot_remove()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        try:
            mat = bpy.data.materials['defaultName']
            patchindex = list(obj.data.materials).index(mat)
            obj.active_material_index = patchindex
        except:
            mat = bpy.data.materials.new('defaultName')
            mat.diffuse_color = (0.5,0.5,0.5)
            bpy.ops.object.material_slot_add()
            obj.material_slots[-1].material = mat
        mat['patchtype'] = 'wall'
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        return{'FINISHED'}

class OBJECT_OT_SetPatchName(bpy.types.Operator):
    '''Set the given name to the selected faces'''
    bl_idname = "set.patchname"
    bl_label = "Set name"

    def execute(self, context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        NoSelected = 0
        for f in obj.data.polygons:
            if f.select:
                NoSelected += 1
        if NoSelected:
            namestr = scn.patchName
            namestr = namestr.strip()
            namestr = namestr.replace(' ', '_')
            try:
                mat = bpy.data.materials[namestr]
                patchindex = list(obj.data.materials).index(mat)
                obj.active_material_index = patchindex
            except: # add a new patchname (as a blender material, as such face props are conserved during mesh mods)
                mat = bpy.data.materials.new(namestr)
                mat.diffuse_color = patchColor(len(obj.data.materials)-1)
                bpy.ops.object.material_slot_add()
                obj.material_slots[-1].material = mat
            mat['patchtype'] = scn.bcTypeEnum
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.material_slot_assign()
        else:
            self.report({'INFO'}, "No faces selected!")
            return{'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_setBoundaryLayerY(bpy.types.Operator):
    '''Sets cell size in y direction in boundary layer edges'''
    bl_idname = "set.boundarylayery"
    bl_label = "Set all boundary layers"

    def execute(self,context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        dx1l = bm.edges.layers.float.get('dx1')
        dx2l = bm.edges.layers.float.get('dx2')
        exp1l = bm.edges.layers.float.get('exp1')
        exp2l = bm.edges.layers.float.get('exp2')
        maxdxl = bm.edges.layers.float.get('maxdx')
        bl1l = bm.edges.layers.int.get('bl1')
        bl2l = bm.edges.layers.int.get('bl2')
        timel = bm.edges.layers.float.get('time')
        copyAlignedl = bm.edges.layers.int.get('copyAligned')

       


        # For older versions of Blender
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()
        
         #Curve deleting
        curves = bpy.data.curves
        objects = bpy.data.objects
        scene = bpy.context.scene

        # remove the object
        for o in bpy.data.objects:
            if "blflags" in o.name:
                #print(o.name)
                cu=o.data
                scene.objects.unlink(o)
                objects.remove(o)

        #Curve deleting ends

        anyselected = False

        for e in bm.edges:
            if e[bl1l] == 0:
                e[dx1l] = 0.0;
                e[exp1l] = 1.0;
            if e[bl1l] == 1:
                e[dx1l] = scn.bldx1
                e[exp1l] = scn.blexp1
                inboundline = [e.verts[1].co[:], e.verts[0].co[:]]
                createLine('bl', inboundline, scn.blexp1,scn.bldx1,'bl1')
            if e[bl1l] == 2:
                e[dx1l] = scn.bldx2
                e[exp1l] = scn.blexp2
                inboundline = [e.verts[1].co[:], e.verts[0].co[:]]
                createLine('bl', inboundline, scn.blexp2,scn.bldx2,'bl2')
            if e[bl2l] == 0:
                e[dx2l] = 0.0;
                e[exp2l] = 1.0;
            if e[bl2l] ==1:
                e[dx2l] = scn.bldx1
                e[exp2l] = scn.blexp1
                inboundline = [e.verts[0].co[:], e.verts[1].co[:]]
                createLine('bl', inboundline, scn.blexp1,scn.bldx1,'bl1')  
            if e[bl2l] == 2:
                e[dx2l] = scn.bldx2
                e[exp2l] = scn.blexp2
                inboundline = [e.verts[0].co[:], e.verts[1].co[:]]
                createLine('bl', inboundline, scn.blexp2,scn.bldx2,'bl2')
            
            
            # blender float cannot store very big floats
           
        anyselected = True
        if anyselected:
            bmesh.update_edit_mesh(obj.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
#        printedgeinfo()
        return {'FINISHED'}



    
class OBJECT_OT_DeleteBoundaryLayer(bpy.types.Operator):
    '''Delete boundary layer flags'''
    bl_idname = "del.bl"
    bl_label = "Delete boundary layer flags"

    def execute(self, context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
         #Curve deleting
        curves = bpy.data.curves
        objects = bpy.data.objects
        scene = bpy.context.scene
        # remove the object
        for o in bpy.data.objects:
            if "blflags" in o.name:
                cu=o.data
                scene.objects.unlink(o)
                objects.remove(o)
        #Curve deleting ends
        return{'FINISHED'}        
    
    
    
    
class OBJECT_OT_InitBL(bpy.types.Operator):
    '''Initialises boundary layer flags'''
    bl_idname = "init.boundarylayer"
    bl_label = "Initialise boundary layer flags"
    def execute(self, context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.layers.int.new("bl1")
        bm.edges.layers.int.new("bl2")
        return{'FINISHED'}
    



class OBJECT_OT_GlobalMax(bpy.types.Operator):
    '''Sets max cell size for all edge(s)'''
    bl_idname = "set.globalmax"
    bl_label = "Set globalmax"

    def execute(self,context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        maxdxl = bm.edges.layers.float.get('maxdx')
        bl1l = bm.edges.layers.int.get('bl1')
        bl2l = bm.edges.layers.int.get('bl2')
       
       
        # For older versions of Blender
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()

        anyselected = False
        for e in bm.edges:      
            if e[bl1l] != 3 and e[bl2l] != 3:
                e[maxdxl] = scn.globalMax
                
            
            
            # blender float cannot store very big floats
           
            anyselected = True

        if anyselected:
            bmesh.update_edit_mesh(obj.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
#        printedgeinfo()
        return {'FINISHED'}

class OBJECT_OT_SetEdge(bpy.types.Operator):
    '''Sets edge(s) properties'''
    bl_idname = "set.edges"
    bl_label = "Set edges"
    def execute(self,context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        dx1l = bm.edges.layers.float.get('dx1')
        dx2l = bm.edges.layers.float.get('dx2')
        exp1l = bm.edges.layers.float.get('exp1')
        exp2l = bm.edges.layers.float.get('exp2')
        bl1l = bm.edges.layers.int.get('bl1')
        bl2l = bm.edges.layers.int.get('bl2')
        cellsl = bm.edges.layers.int.get('cells')
        maxdxl = bm.edges.layers.float.get('maxdx')
        timel = bm.edges.layers.float.get('time')
        copyAlignedl = bm.edges.layers.int.get('copyAligned')

        # For older versions of Blender
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()

        anyselected = False
        for e in bm.edges:
            if e.select == True:
                e[dx1l] = scn.dx1
                e[dx2l] = scn.dx2
                e[exp1l] = scn.exp1
                e[exp2l] = scn.exp2
                e[bl1l] = scn.bl1
                e[bl2l] = scn.bl2
                e[maxdxl] = scn.maxdx
                e[cellsl] = scn.cells
                # blender float cannot store very big floats
                e[timel]=time.time()-1437000000
                e[copyAlignedl]=scn.copyAligned
                anyselected = True
        if anyselected:
            bmesh.update_edit_mesh(obj.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
#        printedgeinfo()
        return {'FINISHED'}

def printedgeinfo():
    obj = bpy.context.active_object
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    dx1l = bm.edges.layers.float.get('dx1')
    dx2l = bm.edges.layers.float.get('dx2')
    exp1l = bm.edges.layers.float.get('exp1')
    exp2l = bm.edges.layers.float.get('exp2')
    cellsl = bm.edges.layers.int.get('cells')
    maxdxl = bm.edges.layers.float.get('maxdx')
    timel = bm.edges.layers.float.get('time')
    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()
    string = ''
    print('{:>6}{:>6}{:>6}{:>6}{:>6}{:>6}{:>6}{:>6}{:>12}'.format(\
    'eidx','ver1','ver2','dx1','dx2','grow1','grow2','maxdx','time'))
    for idx,e in enumerate(bm.edges):
        string += '{:6}{:6}{:6}{:{numbers}.{decimals}g}{:{numbers}.{decimals}g}\
{:{numbers}.{decimals}g}{:{numbers}.{decimals}g}\
{:{numbers}.{decimals}g}{:12.0f}'.format(\
                  idx,e.verts[0].index,e.verts[1].index,e[dx1l],e[dx2l],\
                  e[exp1l],e[exp2l],e[maxdxl],e[timel],\
                  numbers=6,decimals=2)+'\n'
    print(string)


class OBJECT_OT_GetEdge(bpy.types.Operator):
    '''Get edge(s) properties'''
    bl_idname = "get.edges"
    bl_label = "Get edges"
    def execute(self,context):
        scn = context.scene
        obj = context.active_object

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        dx1l = bm.edges.layers.float.get('dx1')
        dx2l = bm.edges.layers.float.get('dx2')
        exp1l = bm.edges.layers.float.get('exp1')
        exp2l = bm.edges.layers.float.get('exp2')
        bl1l = bm.edges.layers.int.get('bl1')
        bl2l = bm.edges.layers.int.get('bl2')
        cellsl = bm.edges.layers.int.get('cells')
        maxdxl = bm.edges.layers.float.get('maxdx')
        copyAlignedl = bm.edges.layers.int.get('copyAligned')
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()
        anyselected = False
        for e in bm.edges:
            if e.select == True:
                scn.dx1=e[dx1l]
                scn.dx2=e[dx2l]
                scn.exp1=e[exp1l]
                scn.exp2=e[exp2l]
                scn.bl1=e[bl1l]
                scn.bl2=e[bl2l]
                scn.cells=e[cellsl]
                scn.maxdx=e[maxdxl]
                scn.copyAligned=e[copyAlignedl]
                anyselected = True
                break
        if anyselected:
            bmesh.update_edit_mesh(obj.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
        return {'FINISHED'}




class OBJECT_OT_FindBroken(bpy.types.Operator):
    '''Detect blocks and mark unused edges'''
    bl_idname = "find.broken"
    bl_label = "Diagnose"

    def execute(self, context):
        from . import utils
        import imp
        imp.reload(utils)
        from . import blender_utils
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        verts = list(blender_utils.vertices_from_mesh(obj))
        edges = list(blender_utils.edges_from_mesh(obj))
        refEdges = list(blender_utils.edges_from_mesh(obj))

        log, block_print_out, dependent_edges, face_info, all_edges, faces_as_list_of_nodes = utils.blockFinder(edges, verts, '','', [])
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,True,False)")
        for e in obj.data.edges:
            e.select = True

        def edgeFinder(v0, v1, edgeList):
            if [v0, v1] in edgeList:
                return edgeList.index([v0, v1])
            if [v1, v0] in edgeList:
                return edgeList.index([v1, v0])
            return -1

        edgeOrder = [[0,1], [1,2], [2,3], [0,3], [4,5], [5,6], [6,7], [4,7], [0,4], [1,5], [2,6], [3,7]]
        for vl in block_print_out:
            for e in edgeOrder:
                v0 = vl[e[0]]
                v1 = vl[e[1]]
                obj.data.edges[edgeFinder(v0, v1, refEdges)].select = False

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class OBJECT_OT_RepairFaces(bpy.types.Operator):
    '''Delete internal face and create boundary faces'''
    bl_idname = "repair.faces"
    bl_label = "Repair"

    c = EnumProperty(
        items = [('wall', 'wall', 'Defines the patch as wall'),
                 ('patch', 'patch', 'Defines the patch as generic patch'),
                 ('empty', 'empty', 'Defines the patch as empty'),
                 ('symmetryPlane', 'symmetryPlane', 'Defines the patch as symmetryPlane'),
                 ],
        name = "Patch type")

    def execute(self, context):
        from . import utils
        import imp
        imp.reload(utils)
        from . import blender_utils

        removeInternal = bpy.context.scene.removeInternal
        createBoundary = bpy.context.scene.createBoundary

        if not createBoundary and not removeInternal:
            self.report({'INFO'}, "Repair: Nothing to do!")
            return{'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        verts = list(blender_utils.vertices_from_mesh(obj))
        edges = list(blender_utils.edges_from_mesh(obj))

        disabled = []
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
        for group in obj.vertex_groups:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            if group.name == 'disabled':
                bpy.ops.object.vertex_group_set_active(group=group.name)
                bpy.ops.object.vertex_group_select()
                bpy.ops.object.mode_set(mode='OBJECT')
                for v in obj.data.vertices:
                    if v.select == True:
                        disabled += [v.index]

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        nRemoved, nCreated = utils.repairFaces(edges, verts, disabled, obj, removeInternal, createBoundary)
        self.report({'INFO'}, "Created {} boundary faces and removed {} internal faces".format(nCreated, nRemoved))
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=200)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        scn = context.scene
        obj = context.object
        nPatches = obj.material_slots.__len__()
        self.layout.prop(scn, "removeInternal")
        self.layout.prop(scn, "createBoundary")
        self.layout.label("Assign new faces to patch")
        self.layout.template_list("MATERIAL_UL_matslots", "", obj, "material_slots", obj, "active_material_index", rows=nPatches)


class OBJECT_OT_GetPatch(bpy.types.Operator):
    '''Click to select faces belonging to this patch'''
    bl_idname = "set.getpatch"
    bl_label = "Get patch"

    whichPatch = StringProperty()

    def execute(self, context):
        scn = context.scene
        obj = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mat = bpy.data.materials[self.whichPatch]
        patchindex = list(obj.data.materials).index(mat)
        obj.active_material_index = patchindex
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_select()
        scn.bcTypeEnum = mat['patchtype']
        scn.patchName = self.whichPatch
        return {'FINISHED'}

class OBJECT_OT_createPreview(bpy.types.Operator):
    '''Creates a mesh preview as a separate object'''
    bl_idname = "create.preview"
    bl_label = "Preview"
    def execute(self, context):
        from . import preview
        import imp
        imp.reload(preview)
        try:
            mesh=preview.PreviewMesh()
        except RuntimeError:
            self.report({'INFO'}, 'ERROR: No BlockMesh Found!')
            return{'CANCELLED'}

        cells = writeBMD(mesh.tempdir+'/constant/polyMesh/blockMeshDict')
        mesh.generateMesh()
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return{'FINISHED'}




class OBJECT_OT_deletePreview(bpy.types.Operator):
    '''Delete preview mesh object'''
    bl_idname = "delete.preview"
    bl_label = "Delete preview mesh"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        name = ''
        for obj in bpy.data.objects:
            try:
                name = obj['swiftBlockObj']
            except:
                obj.select = False
        bpy.ops.object.delete()
        try:
            obj = bpy.data.objects[name]
            obj.select = True
            obj.hide = False
            bpy.context.scene.objects.active = obj
        except:
            pass
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        return {'FINISHED'}



class EdgeInfo:
    edge=None
    v1=None
    v2=None
    dx1=None
    dx2=None
    exp1=None
    exp2=None
    maxdx=None
    cells=None
    length=None
    time=None
    inverse=None
    copyAligned=None

class OBJECT_OT_writeBMD(bpy.types.Operator):
    '''Writes out a blockMeshDict file for the currently selected object'''
    bl_idname = "write.bmdfile"
    bl_label = "Write"

    if "bpy" in locals():
        import imp
        if "utils" in locals():
            imp.reload(utils)
        if "blender_utils" in locals():
            imp.reload(blender_utils)

    filepath = StringProperty(
            name="File Path",
            description="Filepath used for exporting the file",
            maxlen=1024,
            subtype='FILE_PATH',
            default='/opt',
            )
    check_existing = BoolProperty(
            name="Check Existing",
            description="Check and warn on overwriting existing files",
            default=True,
            options={'HIDDEN'},
            )

    logging = BoolProperty(
            name="Log",
            description="Click to enable log files",
            default=False
            )

    def invoke(self, context, event):
        if context.scene.setEdges:
            try:
                bpy.data.objects[context.scene.geoobjName]
            except:
                self.report({'INFO'}, "Cannot find object for edges!")
                return{'CANCELLED'}
        try:
            self.filepath = context.active_object['path']
        except:
            self.filepath = 'blockMeshDict'
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        cells = writeBMD(self.filepath)
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return{'FINISHED'}


class BuildBlocking(bpy.types.Operator):
    bl_idname = "build.blocking"
    bl_label = "align and clean blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        from . import utils
        # get verts and edges
        ob = context.active_object
        mesh = ob.data
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        verts = []
        edges = []
        for v in mesh.vertices:
            verts.append(v.co)
        for e in mesh.edges:
            edges.append([e.vertices[0],e.vertices[1]])
        stime = time.time()

        # find blocking
        log, block_verts, dependent_edges, face_info, all_edges, faces_as_list_of_nodes = utils.blockFinder(edges,verts, '','', [])

        # KOPIOI 1
        # Save the blocking for previewing
        ob.block_verts.clear()
        for bv in block_verts:
            b = ob.block_verts.add()
            b.block_verts = bv

        # KOPIOI 2 ja funktio
        # align the edge blocks into same direction
        align_edges(block_verts, dependent_edges)

        # KOPIOI 3 (ei valttamaton)
        # remove internal faces and build boundary faces
        repair_faces(face_info, faces_as_list_of_nodes)
        return {"FINISHED"}

class BlockProperty(bpy.types.PropertyGroup):
    block_verts = bpy.props.IntVectorProperty(size = 8)
bpy.utils.register_class(BlockProperty)

bpy.types.Object.block_verts = \
    bpy.props.CollectionProperty(type=BlockProperty)

def edge(e0, e1):
    return [min(e0,e1), max(e0,e1)]

def align_edges(block_print_out, dependent_edges):
    bpy.ops.object.mode_set(mode='OBJECT')
    edgeDirections = [set() for i in dependent_edges]
    positiveBlockEdges = [[(0,1),(3,2),(7,6),(4,5)],[(0,3),(1,2),(5,6),(4,7)],[(0,4),(1,5),(2,6),(3,7)]]
    for i in range(1000):
        ready = True
        for ed, de in zip(edgeDirections,dependent_edges):
            if not len(ed)==len(de):
                ready = False
        if ready:
            break
        for bid, vl in enumerate(block_print_out):
            for es, edgeSet in enumerate(dependent_edges):
                for direction in range(3):
                    if edge(vl[positiveBlockEdges[direction][0][0]],vl[positiveBlockEdges[direction][0][1]]) in edgeSet:
                        if not edgeDirections[es]:
                            edgeDirections[es] = set([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                        else:
                            simedges = edgeDirections[es].intersection([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                            if simedges:
                                edgeDirections[es] |= set([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                            else:
                                asimedges= set(edgeDirections[es]).intersection([(vl[e[1]],vl[e[0]]) for e in positiveBlockEdges[direction]])
                                if asimedges:
                                    edgeDirections[es] |= set([(vl[e[1]],vl[e[0]]) for e in positiveBlockEdges[direction]])

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

def findFace(faces, vl):
    for fid, f in enumerate(faces):
        if vl[0] in f and vl[1] in f and vl[2] in f and vl[3] in f:
            return fid, f
    return -1, []

# Kalle's implementation
def repair_faces(face_info, faces_as_list_of_nodes):
    ob = bpy.context.active_object
    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for f in ob.data.polygons:
        fid, tmp = findFace(faces_as_list_of_nodes, f.vertices)
        if fid >= 0: # face was found in list
            if (len(face_info[fid]['neg']) + len(face_info[fid]['pos'])) > 1: #this is an internal face
                f.select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    presentFaces = []

    for f in ob.data.polygons:
        presentFaces.append(list(f.vertices))

    for faceid, f in enumerate(faces_as_list_of_nodes):
        if (len(face_info[faceid]['neg']) + len(face_info[faceid]['pos'])) == 1: #this is a boundary face
            fid, tmp = findFace(presentFaces, f)
            if fid < 0: # this boundary face does not exist as a blender polygon. lets create one!
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
                for v in f:
                    ob.data.vertices[v].select = True
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.edge_face_add()
                bpy.ops.mesh.tris_convert_to_quads(uvs=False, vcols=False, sharp=False, materials=False)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
def writeBMD(filepath, showAll=True):
    import locale
    from . import utils
    import imp
    imp.reload(utils)
    from . import blender_utils
    locale.setlocale(locale.LC_ALL, '')

    stime = time.time()

    scn = bpy.context.scene
    obj = bpy.context.active_object
    patchnames = list()
    patchtypes = list()
    patchverts = list()
    patches = list()

    bpy.ops.object.mode_set(mode='OBJECT')   # Refresh mesh object
    bpy.ops.object.mode_set(mode='EDIT')

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    vertexNames = []
    disabled = []
    for group in obj.vertex_groups:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        if not group.name[0] == '_':
            bpy.ops.object.vertex_group_set_active(group=group.name)
            bpy.ops.object.vertex_group_select()
            bpy.ops.object.mode_set(mode='OBJECT')
            vlist = []
            for v in obj.data.vertices:
                if v.select == True:
                    vlist += [v.index]
            if vlist:
                if group.name == 'disabled':
                    disabled = vlist
                else:
                    vertexNames.append([group.name, vlist])

    bpy.ops.object.mode_set(mode='EDIT')
    for mid, m in enumerate(obj.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        obj.active_material_index = mid
        bpy.ops.object.material_slot_select()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        faces = obj.data.polygons
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

    verts = list(blender_utils.vertices_from_mesh(obj))
    edges = list(blender_utils.edges_from_mesh(obj))

    bpy.ops.object.mode_set(mode='OBJECT')

    obj.select = False
    if scn.setEdges:
        polyLines, polyLinesPoints, lengths = getPolyLines(verts, edges, obj)
    else:
        polyLines = ''
        lengths = [[], []]
    bpy.context.scene.objects.active = obj
    obj.select = True
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)
    dx1l = bm.edges.layers.float.get('dx1')
    dx2l = bm.edges.layers.float.get('dx2')
    exp1l = bm.edges.layers.float.get('exp1')
    exp2l = bm.edges.layers.float.get('exp2')
    maxdxl = bm.edges.layers.float.get('maxdx')
    cellsl = bm.edges.layers.int.get('cells')
    timel = bm.edges.layers.float.get('time')
    copyAlignedl = bm.edges.layers.int.get('copyAligned')
    if hasattr(bm.edges, "ensure_lookup_table"):
        bm.edges.ensure_lookup_table()
    edgeInfo = dict()
    for eidx,e in enumerate(bm.edges):
        edge1 = EdgeInfo()
        edge1.edge=eidx
        edge1.dx1=e[dx1l]
        edge1.dx2=e[dx2l]
        edge1.exp1=e[exp1l]
        edge1.exp2=e[exp2l]
        edge1.cells=e[cellsl]
        edge1.maxdx=e[maxdxl]
        edge1.time=e[timel]
        edge1.copyAligned=e[copyAlignedl]
        edge1.inverse=True
        edge2 = EdgeInfo()
        edge2.edge=eidx
        edge2.dx2=e[dx1l]
        edge2.dx1=e[dx2l]
        edge2.exp2=e[exp1l]
        edge2.exp1=e[exp2l]
        edge2.cells=e[cellsl]
        edge2.maxdx=e[maxdxl]
        edge2.time=e[timel]
        edge2.copyAligned=e[copyAlignedl]
        edge2.inverse=False

        # There must be one edge with largest fraction for blockMesh.
        if edge1.dx1>0 and edge1.exp1>1 and edge1.dx1 == edge1.dx2\
            and edge1.exp1== edge1.exp2:
            edge1.dx1 += 1.e-6
            edge2.dx2 += 1.e-6
        ev = list([e.verts[0].index,e.verts[1].index])
        if ev in lengths[0]:
            ind = lengths[0].index(ev)
            length = lengths[1][ind]
        elif [ev[1],ev[0]] in lengths[0]:
            ind = lengths[0].index([ev[1],ev[0]])
            length = lengths[1][ind]
        else:
            length = (verts[ev[0]] - verts[ev[1]]).magnitude
        if length < 1e-6:
            self.report({'INFO'}, "Zero length edge detected, check block structure!")
            return{'FINISHED'}
        edge1.length=length
        edge2.length=length
        edgeInfo[(e.verts[0].index,e.verts[1].index)] = edge2
        edgeInfo[(e.verts[1].index,e.verts[0].index)] = edge1
    NoCells = utils.write(filepath, edges, verts, scn.ctmFloat,
        patches, polyLines, edgeInfo, vertexNames, disabled, False,stime)
    return NoCells

initProperties()

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

