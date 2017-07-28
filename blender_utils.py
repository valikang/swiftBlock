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

# <pep8 compliant>

import bpy
from mathutils import Vector, Matrix
import bgl
import bmesh



def vertices_from_mesh(ob):
    '''
    '''

    # get the modifiers
    try:
        mesh = ob.to_mesh(bpy.context.scene, False, "PREVIEW")
    except RuntimeError:
        raise StopIteration

    matrix = ob.matrix_world.copy()

    for v in mesh.vertices:
        yield (matrix*v.co)

    bpy.data.meshes.remove(mesh)

def edges_from_mesh(ob):
    '''
    '''

    # get the modifiers
    try:
        mesh = ob.to_mesh(bpy.context.scene, False, "PREVIEW")
    except RuntimeError:
        raise StopIteration

    for e in mesh.edges:
        yield list(e.vertices)

    bpy.data.meshes.remove(mesh)

def activateObject(ob, hideCurrent = False):
    context = bpy.context
    bpy.ops.object.mode_set(mode='OBJECT')
    cob = context.active_object
    cob.hide = hideCurrent
    cob.select = False
    scn = context.scene
    ob.select = True
    ob.hide = False
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')

arrow_head = [
    [-1,-1],
    [0,0],
    [1,-1],
]
def draw_arrow_head(ob, vecFrom, vecTo):
    if ob is None:
        return

    direction = Vector(vecTo) - Vector(vecFrom)
    direction.resize_2d()
    angle = direction.angle(Vector((0,1)))

    # form a 2d rotation matrix
    mat = Matrix().Rotation(angle, 2)

    # middle point
    middle = (Vector(vecTo) + Vector(vecFrom)) / 2.0
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0.0,0.0,0.0,0.5)
    bgl.glLineWidth(2)

    bgl.glBegin(bgl.GL_LINE_STRIP)
    for v in arrow_head:
        xy = Vector(v)* 4.0 * mat
        xy.resize_3d()
        newPos = xy + middle
        print(newPos)
        bgl.glVertex3f(*newPos)
    bgl.glEnd()

def draw_edge_direction(self,context):
    ob = bpy.context.active_object
    if ob is None:
        return
    if bpy.context.active_object.mode != 'EDIT':
        return
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    for e in bm.edges:
        draw_arrow_head(ob, e.verts[0].co, e.verts[1].co)

class EdgeVisualiser(bpy.types.Operator):
    bl_idname = "edge.visualiser"
    bl_label = "Edge Visualiser"
    bl_description = "Show edge directions"

    _handle = None

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def modal(self, context, event):
        context.area.tag_redraw()
        if context.area:

        # removal of callbacks when operator is called again
        # if context.scene.display_indices == -1:
            # bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            # context.scene.display_indices = 0
            return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def invoke(self, context, event):
        if context.area.type == "VIEW_3D":
            # operator is called for the first time, start everything
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_edge_direction, (self, context), 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.report({"WARNING"}, "View3D not found, can't run operator")
            return {"CANCELLED"}


def previewMesh(ob, points, faces):
    blocking = ob
    blocking.hide = True
    blocking.select = False
    scn = bpy.context.scene
    if not ob.preview_object or not ob.preview_object in bpy.data.objects:
        mesh_data = bpy.data.meshes.new("previewMesh")
        previewMeshOb = bpy.data.objects.new('previewMesh', mesh_data)
        previewMeshOb.ispreviewObject = True
        scn.objects.link(previewMeshOb)
        ob.preview_object = previewMeshOb.name
    else:
        previewMeshOb = bpy.data.objects["previewMesh"]
        oldme = previewMeshOb.data
        mesh_data = bpy.data.meshes.new("previewMesh")
        previewMeshOb.data = mesh_data
        bpy.data.meshes.remove(oldme)
    previewMeshOb.hide = False
    previewMeshOb.select = True
    mesh_data.from_pydata(points, [], faces)
    mesh_data.update()

    scn.objects.active = previewMeshOb
    bpy.context.object.data.show_extra_edge_length = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    previewMeshOb.show_all_edges = True
    previewMeshOb.show_wire = True

def initDependentEdges(ob):
    me = ob.data
    detemp = []
    ngroups = 0
    edges = list(edges_from_mesh(ob))
    # aligned_edges = [[] for i in range(len(edges))]
    def edgeFinder(v0, v1, edgeList):
        if [v0, v1] in edgeList:
            return edgeList.index([v0, v1])
        if [v1, v0] in edgeList:
            return edgeList.index([v1, v0])
        return -1

    for de in ob.dependent_edges:
        detemp.append(list(de.dependent_edge))
        ngroups = max(ngroups,int(de.dependent_edge[0]))

    dependent_edges = [[] for i in range(ngroups+1)]
    for e in detemp:
        i = edgeFinder(e[1],e[2],edges)
        dependent_edges[e[0]].append(me.edges[i])

    ob['aligned_group'] = dependent_edges
    # dependent_edges = [[] for i in range(ngroups+1)]
    # for e in detemp:
        # i = edgeFinder(e[1],e[2],edges)
        # dependent_edges[e[0]].append([e[1],e[2]])
    # dependent_edges = [[] for i in range(ngroups+1)]
    # for e in detemp:
        # dependent_edges[e[0]].append([e[1],e[2]])
        # i = edgeFinder(e[1],e[2],edges)
        # aligned_edges[i] = e[0]
    # print(aligned_edges)
    # for de in dependent_edges:
