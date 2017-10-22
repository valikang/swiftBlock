bl_info = {
    "name": "SwiftBlock,Mikko with global variable toolbox",
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

from bpy.props import *


from mathutils import Vector
from math import fabs, degrees, radians, sqrt, cos, sin, pi

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
    if blType == "g1":
        lmat.diffuse_color = (0.0,0.0,1.0)
    if blType == "g2":
        lmat.diffuse_color = (1.0,0.0,0.0)
    lmat.use_shadeless = True
    theLine.data.materials.append(lmat)

####And coloring ends here


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
            split = box.split(percentage=0.5)
            split.operator("build.blocking", text="Build Blocking")
            split.prop(ob, "useNumba")

            split = box.split()
            split.operator("preview.mesh", text="Preview mesh")
            split = split.split()
            split.operator("write.mesh", text="Write mesh")
            box.template_list("block_items", "", ob, "blocks", ob, "block_index", rows=2)
            box.operator("get.block")

            box = self.layout.box()
            box.label("Edge mapping")
            # box.prop(ob, "MappingType")
            split = box.split()
            split.prop(ob, "Cells")
            # split.operator('set.cellsize')
            if ob.Mesher == "blockMeshMG":
                split = box.split()
                col = split.column()
                col.label("Start")
                col.prop(ob, "x1")
                col.prop(ob, "r1")
                #Turo added
                col.prop(ob, "g1")
                #Turo added ends
                col = split.column()
                col.label("End")
                col.prop(ob, "x2")
                col.prop(ob, "r2")
                
                #Turo added
                col.prop(ob, "g2")
                #Turo added ends                


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

            #Turo added
            box = self.layout.box()
            #box = box.column()
            box.label("Global variables (not if bl=3)")

            box.prop(ob,'setGlobalCellMax')
            if ob.setGlobalCellMax:
                box.prop(ob,'globalCellMax')
                box = box.column()
                box.operator('set.globalcell')

            box.prop(ob,'setGlobalGroups')
            if ob.setGlobalGroups:
                box.prop(ob,'gx1')
                box.prop(ob,'gr1')
                box.prop(ob,'gx2')
                box.prop(ob,'gr2')
                box = box.column()
                box.operator('set.globalgroups')
                box.prop(ob,'initGlobal')
                if ob.initGlobal:
                    box.operator('init.globalgroups')
                box.prop(ob,'delGlobalFlags')
                if ob.delGlobalFlags:
                    box.operator('del.globalflags')
             #Turo added ends
                    
            box = self.layout.box()
            box.label("Projections")
            split = box.split()
            split.prop(ob, "ProjectionObject","",icon = "OUTLINER_OB_SURFACE")
            split.operator("add.projections", text="Add")
            split.operator("remove.projections", text="Remove")
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
            box.prop(ob,"ShowInternalFaces")

            
            box = self.layout.box()
            box.label('Boundary conditions')
            row = box.row()
            row.template_list("boundary_items", "", ob.data, "materials", ob, "boundary_index", rows=2)
            col = row.column(align=True)
            col.operator("boundaries.action", icon='ZOOMIN', text="").action = 'ADD'
            col.operator("boundaries.action", icon='ZOOMOUT', text="").action = 'REMOVE'
            row = self.layout.row()
            row.operator('boundaries.action', 'Assign').action = 'ASSIGN'

def initSwiftBlockProperties():
    bpy.types.Object.isblockingObject = bpy.props.BoolProperty(default=False)
    bpy.types.Object.blocking_object = bpy.props.StringProperty(default="")
    bpy.types.Object.ispreviewObject = bpy.props.BoolProperty(default=False)
    bpy.types.Object.preview_object = bpy.props.StringProperty(default='')
    bpy.types.Object.direction_object = bpy.props.StringProperty(default="")
    bpy.types.Object.isdirectionObject = bpy.props.BoolProperty(default=False)

    bpy.types.Object.Mesher = bpy.props.EnumProperty(name="",
            items = (("blockMeshMG","blockMeshMG","",1),
                     ("blockMeshBodyFit","blockMeshBodyFit","",2),),update=changeMesher)


# Blocking properties
    bpy.types.Object.blocks = \
        bpy.props.CollectionProperty(type=BlockProperty)
    bpy.types.Object.block_index = bpy.props.IntProperty()
    bpy.types.Object.useNumba = bpy.props.BoolProperty(default=False, name="Use Numba?")


# Projection/snapping properties
    bpy.types.Object.projections = \
        bpy.props.CollectionProperty(type=ProjectionProperty)
    bpy.types.Object.projection_index = bpy.props.IntProperty()

    bpy.types.Object.Autosnap = bpy.props.BoolProperty(name="Automatic edge projection",
            description = "Snap lines automatically from geometry?")
    bpy.types.Object.ShowInternalFaces = bpy.props.BoolProperty(name="Show Internal Faces",
            default=False, update=showInternalFaces)
    bpy.types.Object.ProjectionObject = bpy.props.EnumProperty(name="Projection object", 
            items=getProjectionObjects, description = "Projection object")
    bpy.types.Object.EdgeSnapObject = bpy.props.EnumProperty(name="Object", 
            items=getProjectionObjects, description = "Projection object")

# Mapping properties
    bpy.types.Object.MappingType = bpy.props.EnumProperty(name="",
            items = (("Geometric MG","Geometric MG","",1),
                     ("Geometric","Geometric","",2),))
    # bpy.types.Object.Dx = bpy.props.FloatProperty(name="dx", default=1, update=setCellSize, min=0)
    bpy.types.Object.Cells = bpy.props.IntProperty(name="Cells", default=10,  min=1)
    bpy.types.Object.x1 = bpy.props.FloatProperty(name="x1", default=0, description="First cell size", min=0)
    bpy.types.Object.x2 = bpy.props.FloatProperty(name="x2", default=0, description="Last cell size",  min=0)
    bpy.types.Object.r1 = bpy.props.FloatProperty(name="r1", default=1.2, description="First boundary layer geometric ratio", min=1.0)
    bpy.types.Object.r2 = bpy.props.FloatProperty(name="r2", default=1.2, description="Last boundary layer geometric ratio", min=1.0)
    bpy.types.Object.Ratio = bpy.props.FloatProperty(name="Ratio", default=1.0, description="Ratio of first cell to last cell", min=0)
    bpy.types.Object.SearchLength = bpy.props.FloatProperty(name="Search Length", default=1.0, description="", min=0)
    # bpy.types.Object.ShowEdgeDirections = bpy.props.BoolProperty(name="Show directions", default=True, update = updateEdgeDirections, description="Show edge directions?")

    #Turo added
#Global boundary layer properties
    bpy.types.Object.setGlobalCellMax = bpy.props.BoolProperty(name="Set globall cell rules?",
            description = "Do you want to set a global maximum cell number?")
    bpy.types.Object.setGlobalGroups = bpy.props.BoolProperty(name="Set global x and r rules?",
            description = "Do you want to set x and r for all edges?")
    bpy.types.Object.initGlobal = bpy.props.BoolProperty(name="Initialize global groups",
            description = "If boundary layers give you an error, try to initialize them?")
    bpy.types.Object.delGlobalFlags = bpy.props.BoolProperty(name="Delete global group flags",
            description = "If you want to hide all the boundary layer flags press this.")

    
    
    bpy.types.Object.g1 = bpy.props.IntProperty(name="g1", default=0, description="Level 1 bondary layer group", min=0)
    bpy.types.Object.g2 = bpy.props.IntProperty(name="g2", default=0, description="Level 2 bondary layer group", min=0)
    bpy.types.Object.globalCellMax = bpy.props.FloatProperty(name="Global cell count", default=0, description="Global cell count", min=1e-6)
    bpy.types.Object.gx1 = bpy.props.FloatProperty(name="Global x1", default=0, description="Global first layer cell size where bl=1", min=1e-6)
    bpy.types.Object.gx2 = bpy.props.FloatProperty(name="Global x2", default=0, description="Global first layer cell size where bl=2", min=1e-6)
    bpy.types.Object.gr1 = bpy.props.FloatProperty(name="Global r1", default=0, description="Global expansion ratio where bl=1", min=1e-6)
    bpy.types.Object.gr2 = bpy.props.FloatProperty(name="Global r2", default=0, description="Global expansion ratio where bl=2", min=1e-6)

    #Turo added ends
    
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

    bpy.types.Object.boundary_index = bpy.props.IntProperty(update=selectActiveBoundary)
    bpy.types.Material.boundary_type = bpy.props.EnumProperty(
        items = [('wall', 'wall',''),
             ('patch', 'patch',''),
             ('empty', 'empty',''),
             ('symmetry', 'symmetry',''),
             ],
        name = "Patch type")

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
        c = split.operator("edit.block", name, emboss=False, icon="UV_FACESEL")
        c.blockid = index
        c.name = block.name

        if block.enabled:
            c = split.operator('enable.block', '',emboss=False,icon="CHECKBOX_HLT").blockid = index
        else:
            c = split.operator('enable.block','', emboss=False,icon="CHECKBOX_DEHLT").blockid = index

class boundary_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = context.active_object
        me = data
        mat = me.materials[index]
        split = layout.split(percentage=0.2)
        split.prop(item, "diffuse_color", '')
        split.prop(item, "name", '', emboss = False)
        split.prop(item, "boundary_type", '', emboss = False)

class boundaries_action(bpy.types.Operator):
    bl_idname = "boundaries.action"
    bl_label = "Boundaries action"

    action = bpy.props.EnumProperty(
        items=(
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
            ('ASSIGN', "Assign", ""),
        )
    )

    def invoke(self, context, event):

        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        if self.action == 'REMOVE':
            mat_name = ob.active_material.name
            ob.data.materials.pop(ob.active_material_index)
            if not bpy.data.materials[mat_name].users:
                bpy.data.materials.remove(bpy.data.materials[mat_name])

        elif self.action == 'ASSIGN':
            for f in bm.faces:
                if f.select:
                    f.material_index = ob.boundary_index
            ob.data.update()

        if self.action == 'ADD':
            name = 'default'
            mat = bpy.data.materials.new(name)
            color = patchColor(len(ob.data.materials))
            mat.diffuse_color = color
            ob.data.materials.append(mat)
            material_index = len(ob.data.materials) - 1

            for f in bm.faces:
                if f.select:
                    f.material_index = material_index
            ob.boundary_index = material_index
            ob.active_material_index = material_index
            ob.data.update()

        return {"FINISHED"}


#Turo added objects

class initGlobalGroups(bpy.types.Operator):
    '''Initialises boundary layer flags'''
    bl_idname = "init.globalgroups"
    bl_label = "Initialise global group system"
    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        bm.edges.layers.int.new("g1")
        bm.edges.layers.int.new("g2")
        return{'FINISHED'}


class setGlobalGroups(bpy.types.Operator):
    '''Sets cell x and r for global groups 1 and 2'''
    bl_idname = "set.globalgroups"
    bl_label = "Set all global groups"
    bl_options = {"UNDO"}

    def execute(self,context):
        scn = context.scene
        ob = context.active_object
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        #bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        #maxdxl = bm.edges.layers.float.get('maxdx')
        g1l = bm.edges.layers.int.get('g1')
        g2l = bm.edges.layers.int.get('g2')

        cellsl = bm.edges.layers.int.get('cells')
        groupl = bm.edges.layers.int.get('groupid')
        timel = bm.edges.layers.int.get('modtime')
        #timel = bm.edges.layers.float.get('time')
        #copyAlignedl = bm.edges.layers.int.get('copyAligned')


        # For older versions of Blender
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()
        
         #Curve deleting
        curves = bpy.data.curves
        objects = bpy.data.objects
        scene = bpy.context.scene

        # remove the object
        for o in bpy.data.objects:
            if o.type == 'CURVE':
                #print(o.name)
                cu=o.data
                scene.objects.unlink(o)
                objects.remove(o)

        #Curve deleting ends

        anyselected = False
        

        for e in bm.edges:
            if e[g1l] == 0:
                e[x1l] = 0.0;
                e[r1l] = 1.0;
            if e[g1l] == 1:
                e[x1l] = ob.gx1
                e[r1l] = ob.gr1
                inboundline = [e.verts[1].co[:], e.verts[0].co[:]]
                createLine('bl', inboundline, ob.gr1,ob.gx1,'g1')
            if e[g1l] == 2:
                e[x1l] = ob.gx2
                e[r1l] = ob.gr2
                inboundline = [e.verts[1].co[:], e.verts[0].co[:]]
                createLine('bl', inboundline, ob.gr2,ob.gx2,'g2')
            if e[g2l] == 0:
                e[x2l] = 0.0;
                e[r2l] = 1.0;
            if e[g2l] ==1:
                e[x2l] = ob.gx1
                e[r2l] = ob.gr1
                inboundline = [e.verts[0].co[:], e.verts[1].co[:]]
                createLine('bl', inboundline, ob.gr1,ob.gx1,'g1')  
            if e[g2l] == 2:
                e[x2l] = ob.gx2
                e[r2l] = ob.gr2
                inboundline = [e.verts[0].co[:], e.verts[1].co[:]]
                createLine('bl', inboundline, ob.gr2,ob.gx2,'g2')
            
            
            # blender float cannot store very big floats
           
        anyselected = True
        if anyselected:
            bmesh.update_edit_mesh(ob.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
#        printedgeinfo()
        return {'FINISHED'}


class globalCellMaxSetter(bpy.types.Operator):
    '''Sets max cell size for all edge(s)'''
    bl_idname = "set.globalcell"
    bl_label = "Set global Cell rules"

    def execute(self,context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(ob.data)
      
        g1l = bm.edges.layers.int.get('g1')
        g2l = bm.edges.layers.int.get('g2')
       
        cellsl = bm.edges.layers.int.get('cells')

        # For older versions of Blender
        if hasattr(bm.edges, "ensure_lookup_table"):
            bm.edges.ensure_lookup_table()

        anyselected = False
        for e in bm.edges:      
            if e[g1l] != 3 and e[g2l] != 3:
                e[cellsl] = ob.globalCellMax
                
            
            
            # blender float cannot store very big floats
           
            anyselected = True

        if anyselected:
            bmesh.update_edit_mesh(ob.data)
        else:
            self.report({'INFO'}, "No edge(s) selected!")
            return{'CANCELLED'}
#        printedgeinfo()
        return {'FINISHED'}


    
class deleteGlobalFlags(bpy.types.Operator):
    '''Delete boundary layer flags'''
    bl_idname = "del.globalflags"
    bl_label = "Delete global group flags"

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



#Turo added projects end

    
    
class projection_items(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.4)
        proj = context.active_object.projections[index]
        if proj.type == 'vert2surf':
            icon = "VERTEXSEL"
        elif proj.type == 'edge2surf':
            icon = "EDGESEL"
        elif proj.type == 'face2surf':
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

class ProjectionProperty(bpy.types.PropertyGroup):
    type = bpy.props.StringProperty() #vert2surf,edge2surf,face2sur,edge2polyline
    id = bpy.props.IntProperty() #bmesh id
    ob = bpy.props.StringProperty()
bpy.utils.register_class(ProjectionProperty)


def updateBoundaryColor(self, context):
    ob = context.active_object
    mat = bpy.data.materials[self.name]
    mat.diffuse_color = self.color

def updateBoundaryName(self, context):
    ob = context.active_object
    mat = bpy.data.materials[self.oldName]
    mat.name = self.name
    self.oldName = mat.name

class EdgeGroupProperty(bpy.types.PropertyGroup):
    group_name = bpy.props.StringProperty()
    group_edges = bpy.props.StringProperty()
bpy.utils.register_class(EdgeGroupProperty)

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
        #Turo added
        bm.edges.layers.int.new("g1")
        bm.edges.layers.int.new("g2")
        bm.edges.layers.int.new("gx1")
        bm.edges.layers.int.new("gx2")
        bm.edges.layers.int.new("gr1")
        bm.edges.layers.int.new("gr2")
        bm.edges.layers.int.new("globalCellMax")


        #Turo added ends

        bm.faces.layers.int.new('pos') # block number on positive side of the face, -1 boundary face
        bm.faces.layers.int.new('neg') # block number on negative side of the face, -1 boundary face
        bm.faces.layers.int.new('enabled') # 0 = disabled, 1 = boundary face, 2 = internal face

        ob.blocks.clear()
        ob.projections.clear()
        ob.edge_groups.clear()
        bpy.ops.boundaries.action("INVOKE_DEFAULT",action='ADD')

        ob.isblockingObject = True
        ob.data.update()
        ob.show_all_edges = True
        ob.show_wire = True
        return {"FINISHED"}

# Blocking and previewing operators
# Automatical block detection.
class BuildBlocking(bpy.types.Operator):
    bl_idname = "build.blocking"
    bl_label = "Build blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)

        verts = []
        edges = []

        for v in bm.verts:
            verts.append(v.co)
        for e in bm.edges:
            edges.append([e.verts[0].index,e.verts[1].index])

        disabled = [] #not needed anymore

        print('Beginning automatic block detection')
        stime = time.time()
        log, block_verts, block_edges, face_info, all_edges, faces_as_list_of_nodes = blockBuilder.blockFinder(edges, verts, disabled = disabled, numba = ob.useNumba)
        print('Found {} blocks in {:.1f} seconds, used Numba={}'.format(len(block_verts), time.time()-stime,ob.useNumba))


        ob.blocks.clear()
        for i,bv in enumerate(block_verts):
            b = ob.blocks.add()
            b.id = i
            b.name = 'block'#_{}'.format(i)
            b.verts = bv

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
        enabledl = bm.faces.layers.int.get('enabled')

        block_faces = []

        for key, value in face_info.items():
            # probably a bug, some extra faces which do not belong to any block
            if not value['neg'] and not value['pos']:
                continue
            verts = [bm.verts[v] for v in faces_as_list_of_nodes[key]]
            f = bm.faces.get(verts)
            if not f:
                f = bm.faces.new(verts)
            f[enabledl] = -1
            block_faces.append(f)
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

        for f in bm.faces:
            if not f in block_faces:
                bm.faces.remove(f)


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
        updateProjections(ob)
        hideFacesEdges(ob, ob.ShowInternalFaces)
        bpy.ops.draw.directions('INVOKE_DEFAULT',show=False)
        self.report({'INFO'}, "Number of blocks: {}".format(len(block_verts)))
        return {"FINISHED"}




# Build the mesh from already existing blocking
def writeMesh(ob, folder = ''):
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

    enabledl = bm.faces.layers.int.get('enabled')
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    projections = {'vert2surf':dict(),'edge2surf':dict(),'face2surf':dict(), 'geo':dict()}
    for p in ob.projections:
        if p.type == 'vert2surf' and any([f[enabledl] for f in bm.verts[p.id].link_faces]):
            key = bm.verts[p.id].index
            if key in projections[p.type]:
                projections[p.type][key] += " {}".format(p.ob)
            else:
                projections[p.type][key] = p.ob
        elif p.type == 'edge2surf' and any([f[enabledl] for f in bm.edges[p.id].link_faces]):
            key = tuple(v.index for v in bm.edges[p.id].verts)
            if key in projections[p.type]:
                projections[p.type][key] += " {}".format(p.ob)
            else:
                projections[p.type][key] = p.ob
        elif p.type == 'face2surf' and bm.faces[p.id][enabledl]:
            key = tuple(v.index for v in bm.faces[p.id].verts)
            projections[p.type][key] = p.ob

    selected_edges = [e.select for e in ob.data.edges]

    boundaries = [{'name':mat.name, 'type':mat.boundary_type, 'faceVerts':[]} for mat in ob.data.materials]
    for f in bm.faces:
        if f[enabledl] == 1:
            boundaries[f.material_index]['faceVerts'].append([v.index for v in f.verts])
    for b in boundaries:
        if not b['faceVerts']:
            boundaries.remove(b)

# return edge selection
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for e,sel in zip(ob.data.edges,selected_edges):
        e.select = sel

### This is everything that is related to blockMesh so a new multiblock mesher could be introduced easily just by creating new preview file ###
    if ob.Mesher == 'blockMeshMG':
        from . import blockMeshMG
        importlib.reload(blockMeshMG)
        if folder:
            mesh = blockMeshMG.PreviewMesh(folder)
        else:
            mesh = blockMeshMG.PreviewMesh()
        # projection_tris = writeProjectionObjects(project_verts,project_edges,project_faces, mesh.geomPath)
        if ob.projections:
            geos = writeProjectionObjects(ob, mesh.geomPath)
            projections['geo'] = geos

        cells = mesh.writeBlockMeshDict(verts, 1, boundaries, polyLines, edgeInfo, block_names, blocks, block_edges, projections)
###############################################################
    elif ob.Mesher == 'blockMeshBodyFit':
        from . import blockMeshBodyFit
        importlib.reload(blockMeshBodyFit)
        if folder:
            mesh = blockMeshBodyFit.PreviewMesh(folder)
        else:
            mesh = blockMeshBodyFit.PreviewMesh()
        writeProjectionObjects(ob, mesh.triSurfacePath, onlyFaces = True)
        cells = mesh.writeBlockMeshDict(verts, 1, boundaries, polyLines, edgeInfo, block_names, blocks, block_edges, projections, ob.SearchLength)
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

    filepath = bpy.props.StringProperty(subtype='DIR_PATH')
    # filepath = bpy.props.StringProperty(
            # name="File Path",
            # description="Filepath used for exporting the file",
            # maxlen=1024,
            # subtype='FILE_PATH',
            # default='/opt',
            # )
    check_existing = bpy.props.BoolProperty(
            name="Check Existing",
            description="Check and warn on overwriting existing files",
            default=True,
            options={'HIDDEN'},
            )

    # use_filter_folder = True

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
        #Turo added
        g1l = bm.edges.layers.int.get('g1')
        g2l = bm.edges.layers.int.get('g2')
        #Turo added ends
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
                    #Turo added
                    e[g1l] = ob.g1
                    e[g2l] = ob.g2
                    #Turo added ends
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
        #Turo added
        g1l = bm.edges.layers.int.get('g1')
        g2l = bm.edges.layers.int.get('g2')
        #Turo added ends
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        cellsl = bm.edges.layers.int.get('cells')

        for e in bm.edges:
            if e.select:
                # e[typel] = str.encode(ob.MappingType)
                 ob.Cells = e[cellsl]
                 ob.x1 = e[x1l]
                 ob.x2 = e[x2l]
                 #Turo added
                 ob.g1 = e[g1l] 
                 ob.g2 = e[g2l]
                 #Turo added ends
                 ob.r1 = e[r1l]
                 ob.r2 = e[r2l]
        return {'FINISHED'}

class SetCellSize(bpy.types.Operator):
    "Calculates the number of cells from maximum cell size"
    bl_idname = "set.cellsize"
    bl_label = "Set cell size"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        cellsl = bm.edges.layers.int.get('cells')
        verts = [v.co for v in bm.verts]
        edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges]

        if ob.Autosnap and ob.EdgeSnapObject:
            polyLines, polyLinesPoints, lengths = getPolyLines(verts, edges, ob)
        else:
            polyLines = []
            lengths = [[]]


        for e in bm.edges:
            if e.select:
                ev = list([e.verts[0].index,e.verts[1].index])
                if ev in lengths[0]:
                    ind = lengths[0].index(ev)
                    L = lengths[1][ind]
                else:
                    L = (e.verts[0].co-e.verts[1].co).length

                e[typel] = str.encode(ob.MappingType)
                N=utils.getCells(ob.x1,ob.x2,ob.r1,ob.r2,L,ob.Dx)
                e[cellsl] = N
                e[x1l] = ob.x1
                e[x2l] = ob.x2
                e[r1l] = ob.r1
                e[r2l] = ob.r2
                print(N)
        return {'FINISHED'}


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
# TODO Projections are saved to a Blender CollectionProperty. At the 
# moment if verts, edges or faces have been deleted, the id might not be  
# up to date anymore. It would make sense to save the projections to bmesh
# layer.
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
        if self.type == 'vert2surf':
            bm.verts.ensure_lookup_table()
            bm.verts[self.id].select = True
        elif self.type == 'edge2surf':
            bm.edges[self.id].select = True
        elif self.type == 'face2surf':
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
        ob = context.active_object
        self.pob = ob.ProjectionObject
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
                addProjection('vert2surf', v.index)

        for e in bm.edges:
            if e.select and self.edges:
                addProjection('edge2surf', e.index)

        for f in bm.faces:
            if f.select and self.faces:
                addProjection('face2surf', f.index)
        return {"FINISHED"}

class RemoveProjection(bpy.types.Operator):
    bl_idname = "remove.projection"
    bl_label = "Remove projection"
    bl_options = {"UNDO"}

    proj_id = bpy.props.IntProperty(default = -1)

    def execute(self, context):
        ob = context.active_object
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
                    if p.type == 'vert2surf' and p.id == v.index:
                        remove_projections.append(i)
        for e in bm.edges:
            if e.select:
                for i,p in enumerate(ob.projections):
                    if p.type == 'edge2surf' and p.id == e.index:
                        remove_projections.append(i)
        for f in bm.faces:
            if f.select:
                for i,p in enumerate(ob.projections):
                    if p.type == 'face2surf' and p.id == f.index:
                        remove_projections.append(i)
        remove_projections = reversed(sorted(remove_projections))
        for i in remove_projections:
            ob.projections.remove(i)
        return {"FINISHED"}

def writeProjectionObjects(ob, path, onlyFaces = False):
    objects = []
    for p in ob.projections:
        if onlyFaces and not p.type == 'face2surf':
            continue
        else:
            objects.append(p.ob)
    objects = set(objects)
    for o in objects:
        sob = bpy.data.objects[o]
        hide = sob.hide
        blender_utils.activateObject(sob)
        bpy.ops.export_mesh.stl('EXEC_DEFAULT',filepath = path + '/{}.stl'.format(o))
        sob.hide = hide
    blender_utils.activateObject(ob)
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

class EdgetoPolyLine(bpy.types.Operator):
    bl_idname = "edge.topolyline"
    bl_label = "Project edge to polyline"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        scn = context.scene
        self.ob = context.active_object
        bm = bmesh.from_edit_mesh(self.ob.data)

        for e in bm.edges:
            if e.select:
                self.edge = e.index

        self.proj_ob = bpy.data.objects[self.ob.ProjectionObject]
        blender_utils.activateObject(self.proj_ob)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'RETURN'}:
            bm = bmesh.from_edit_mesh(self.proj_ob.data)
            selected_edges = []
            projl = bm.edges.layers.string.get("projectionEdgeId")
            if not projl:
                projl = bm.edges.layers.int.new("projectionEdgeId")
                self.proj_ob.data.update()
            for e in bm.edges:
                if e.select:
                    e[projl] = self.edge
            blender_utils.activateObject(self.ob)
            return {'FINISHED'}
        elif event.type in 'ESC':
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}


# This function checks that the vert, edge or face is still there.
# Unfortunately, the projection ids might be wrong if verts, edges
# or faces have been deleted.
def updateProjections(ob):
    bm = bmesh.from_edit_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    remove_projections = []
    for i, p in enumerate(ob.projections):
        try:
            if p.type == 'vert2surf':
                bm.verts[p.id]
            elif p.type == 'edge2surf':
                bm.edges[p.id]
            elif p.type == 'face2surf':
                bm.faces[p.id]
        except IndexError:
            remove_projections.append(i)
    for pid in reversed(sorted(remove_projections)):
        ob.projections.remove(pid)
        
# Boundary condition operators
def selectActiveBoundary(self, context):
    ob = context.active_object
    ob.active_material_index = ob.boundary_index

    bm = bmesh.from_edit_mesh(ob.data)
    bpy.ops.mesh.select_all(action='DESELECT')

    for f in bm.faces:
        if f.material_index == ob.boundary_index:
            f.select = True


def patchColor(patch_no):
    color = [(0.25,0.25,0.25), (1.0,0.,0.), (0.0,1.,0.),(0.0,0.,1.),(0.707,0.707,0),(0,0.707,0.707),(0.707,0,0.707)]
    return color[patch_no % len(color)]



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
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        sel_mode = bpy.context.scene.tool_settings.mesh_select_mode
        bpy.context.scene.tool_settings.mesh_select_mode = (False, True, False)
        selected_faces = []
        for f in bm.faces:
            if f.select:
                selected_faces.append((f,[v for v in f.verts]))
        bpy.ops.mesh.extrude_faces_move()
        for f in selected_faces:
            newf = bm.faces.new(f[1])
            for p in ob.projections:
                if p.type == 'face' and p.id == f[0].index:
                    p.id = newf.index
        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False)
        ob.data.update()
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

def showInternalFaces(self, context):
    ob = context.active_object
    hideFacesEdges(ob, ob.ShowInternalFaces)

def hideFacesEdges(ob, showInternal = False):
    ob.data.update()
    bm = bmesh.from_edit_mesh(ob.data)
    bm.verts.ensure_lookup_table()

    negl = bm.faces.layers.int.get('neg')
    posl = bm.faces.layers.int.get('pos')
    enabledl = bm.faces.layers.int.get('enabled')

    for f in bm.faces:
        if f[negl] != -1 and f[posl] != -1: 
            if (not ob.blocks[f[posl]].enabled and ob.blocks[f[negl]].enabled) \
                    or (ob.blocks[f[posl]].enabled and not ob.blocks[f[negl]].enabled):
                # boundary face
                f.hide_set(False)# = False
                f[enabledl] = 1
            elif not ob.blocks[f[posl]].enabled and not ob.blocks[f[negl]].enabled:
                # both blocks disabled
                f[enabledl] = False
                f.hide = True
            elif showInternal:
                # internal face
                f[enabledl] = 2
                f.hide_set(False)
            else:
                # internal face
                f[enabledl] = 2
                f.hide = True
        elif (f[posl] == -1 and f[negl] != -1): #boundary face
            if ob.blocks[f[negl]].enabled:
                # boundary face
                f.hide_set(False)# = False
                f[enabledl] = 1
            else:
                # boundary block disabled
                f.hide_set(True)
                f[enabledl] = False
        elif (f[posl] != -1 and f[negl] == -1): #boundary face
            if ob.blocks[f[posl]].enabled:
                # boundary face
                f.hide_set(False)
                f[enabledl] = 1
            else:
                # boundary block disabled
                f.hide_set(True)
                f[enabledl] = False

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
