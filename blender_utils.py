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

import bpy
from mathutils import Vector, Matrix, Euler
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
    if cob:
        cob.hide = hideCurrent
        cob.select = False
    scn = context.scene
    ob.select = True
    ob.hide = False
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')


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
    previewMeshOb.blocking_object = blocking.name
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

arrow_head = [
    [-1,-1],
    [0,0],
    [1,-1],
]
def draw_arrow_head(ob, vecFrom, vecTo):
    if ob is None:
        return

    direction = Vector(vecTo) - Vector(vecFrom)
    print(direction)
    # direction.resize_2d()
    # print(direction)
    angle = direction.angle(Vector((0,1,0)))

    # form a 2d rotation matrix
    mat = Matrix().Rotation(angle, 2)

    # middle point
    middle = (Vector(vecTo) + Vector(vecFrom)) / 2.0


    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for v in arrow_head:
        xy = Vector(v)* 1.0 * mat
        xy.resize_3d()
        newPos = xy + middle
        bgl.glVertex3f(*newPos)
        bgl.glLineWidth(2)
        bgl.glColor4f(0.0,0.0,0.0,0.5)
    bgl.glEnd()

    # bgl.glEnable(bgl.GL_BLEND)
    # bgl.glBegin(bgl.GL_LINES)
    # bgl.glVertex3f(*(middle-Vector((1,0,0))))
    # bgl.glVertex3f(*(middle-Vector((-1,0,0))))
    # bgl.glVertex3f(*(middle-Vector((0,1,0))))
    # bgl.glVertex3f(*(middle-Vector((0,-1,0))))
    # print((middle-Vector((1,0,0))),(middle-Vector((-1,0,0))))

def draw_edge_direction(self,context):
    ob = bpy.context.active_object
    if ob is None:
        return
    if bpy.context.active_object.mode != 'EDIT':
        return
    me = ob.data
    bm = bmesh.from_edit_mesh(me)
    # draw_arrow_head(bm.edges[0])
    bgl.glEnable(bgl.GL_BLEND)
    for e in bm.edges:
        draw_arrow_head(ob, e.verts[0].co, e.verts[1].co)
    bgl.glEnd()
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0,0.0,0.0,1.0)

class EdgeVisualiser(bpy.types.Operator):
    bl_idname = "edge.visualiser"
    bl_label = "Edge Visualiser"
    bl_description = "Show edge directions"

    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'ESC':
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def invoke(self, context, event):
        args = (self, context)
        if context.area.type == "VIEW_3D":
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_edge_direction, args, 'WINDOW', 'POST_VIEW')
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.report({"WARNING"}, "View3D not found, can't run operator")
            return {"CANCELLED"}
