bl_info = {
    "name": "CAD/BIM Learning Add-on",
    "author": "Your Name",
    "version": (0, 4),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > CAD/BIM",
    "description": "CAD/BIM learning tools for Blender",
    "category": "3D View",
}

import bpy
import bmesh
import math
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatVectorProperty, FloatProperty, IntProperty, StringProperty, CollectionProperty, BoolProperty
from bpy_extras.view3d_utils import region_2d_to_location_3d, location_3d_to_region_2d
from mathutils import Vector, Quaternion


def get_snap_point(context, mouse_pos):
    best_dist = float('inf')
    best_point = None
    region = context.region
    rv3d = context.space_data.region_3d
    for obj in context.visible_objects:
        if obj.type == 'MESH':
            matrix = obj.matrix_world
            for vert in obj.data.vertices:
                world_pos = matrix @ vert.co
                screen_pos = location_3d_to_region_2d(region, rv3d, world_pos)
                if screen_pos:
                    dist = (Vector((mouse_pos[0], mouse_pos[1])) - screen_pos).length
                    if dist < best_dist and dist < 20:  # 20 pixel snap distance
                        best_dist = dist
                        best_point = world_pos
    return best_point

def set_top_view(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'ORTHO'
                    space.region_3d.view_rotation = Quaternion((1, 0, 0, 0))

def get_white_material():
    mat_name = "CAD_BIM_White_Material"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        emission = nodes.new(type='ShaderNodeEmission')
        emission.inputs[0].default_value = (1, 1, 1, 1)  # White color
        emission.inputs[1].default_value = 1  # Strength
        material_output = nodes.get('Material Output')
        mat.node_tree.links.new(emission.outputs[0], material_output.inputs[0])
    return mat

class CAD_BIM_OT_DrawShape(Operator):
    bl_idname = "cad_bim.draw_shape"
    bl_label = "Draw Shape"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.update_shape(context, event)
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                self.start_drawing(context, event)
            elif event.value == 'RELEASE':
                self.finish_drawing(context)
                return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_drawing(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.start_point = None
        self.end_point = None
        self.shape_object = None
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_3d_point(self, context, event):
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        point = region_2d_to_location_3d(region, rv3d, coord, Vector((0, 0, 0)))
        
        # Apply snapping
        snap_point = get_snap_point(context, (event.mouse_region_x, event.mouse_region_y))
        return snap_point if snap_point else point

    def start_drawing(self, context, event):
        self.start_point = self.get_3d_point(context, event)

    def update_shape(self, context, event):
        if self.start_point:
            self.end_point = self.get_3d_point(context, event)
            self.create_shape(context)

    def finish_drawing(self, context):
        if self.shape_object:
            # Finalize the shape here if needed
            pass

    def cancel_drawing(self, context):
        if self.shape_object:
            bpy.data.objects.remove(self.shape_object, do_unlink=True)

    def create_shape(self, context):
        # This method should be overridden by subclasses
        pass

class CAD_BIM_OT_DrawLine(CAD_BIM_OT_DrawShape):
    bl_idname = "cad_bim.draw_line"
    bl_label = "Draw Line"

    def invoke(self, context, event):
        set_top_view(context)
        return super().invoke(context, event)

    def create_shape(self, context):
        if self.shape_object:
            bpy.data.objects.remove(self.shape_object, do_unlink=True)

        curve_data = bpy.data.curves.new(name="Line", type='CURVE')
        curve_data.dimensions = '3D'
        
        line = curve_data.splines.new(type='POLY')
        line.points.add(1)
        line.points[0].co = (*self.start_point, 1)
        line.points[1].co = (*self.end_point, 1)

        self.shape_object = bpy.data.objects.new("Line", curve_data)
        context.collection.objects.link(self.shape_object)

        # Apply white material
        white_material = get_white_material()
        self.shape_object.data.materials.append(white_material)

class CAD_BIM_OT_DrawRectangle(CAD_BIM_OT_DrawShape):
    bl_idname = "cad_bim.draw_rectangle"
    bl_label = "Draw Rectangle"

    def invoke(self, context, event):
        set_top_view(context)
        return super().invoke(context, event)


    def create_shape(self, context):
        if self.shape_object:
            bpy.data.objects.remove(self.shape_object, do_unlink=True)

        curve_data = bpy.data.curves.new(name="Rectangle", type='CURVE')
        curve_data.dimensions = '3D'
        
        polygon = curve_data.splines.new(type='POLY')
        polygon.points.add(3)
        
        x1, y1, z1 = self.start_point
        x2, y2, z2 = self.end_point
        
        polygon.points[0].co = (x1, y1, z1, 1)
        polygon.points[1].co = (x2, y1, z1, 1)
        polygon.points[2].co = (x2, y2, z1, 1)
        polygon.points[3].co = (x1, y2, z1, 1)
        
        polygon.use_cyclic_u = True

        self.shape_object = bpy.data.objects.new("Rectangle", curve_data)
        context.collection.objects.link(self.shape_object)

        # Apply white material
        white_material = get_white_material()
        self.shape_object.data.materials.append(white_material)

class CAD_BIM_OT_DrawCircle(CAD_BIM_OT_DrawShape):
    bl_idname = "cad_bim.draw_circle"
    bl_label = "Draw Circle"

    def invoke(self, context, event):
        set_top_view(context)
        return super().invoke(context, event)


    def create_shape(self, context):
        if self.shape_object:
            bpy.data.objects.remove(self.shape_object, do_unlink=True)

        curve_data = bpy.data.curves.new(name="Circle", type='CURVE')
        curve_data.dimensions = '3D'
        
        circle = curve_data.splines.new(type='NURBS')
        circle.points.add(7)  # 8 points total for a smooth circle
        
        center = Vector(self.start_point)
        radius = (Vector(self.end_point) - center).length
        
        for i in range(8):
            angle = i * (2 * math.pi / 8)
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = center.z
            circle.points[i].co = (x, y, z, 1)
        
        circle.use_cyclic_u = True

        self.shape_object = bpy.data.objects.new("Circle", curve_data)
        context.collection.objects.link(self.shape_object)

class CAD_BIM_OT_DrawPolygon(CAD_BIM_OT_DrawShape):
    bl_idname = "cad_bim.draw_polygon"
    bl_label = "Draw Polygon"

    sides: IntProperty(default=6, min=3, max=64)

    def invoke(self, context, event):
        set_top_view(context)
        return super().invoke(context, event)

    def create_shape(self, context):
        if self.shape_object:
            bpy.data.objects.remove(self.shape_object, do_unlink=True)

        curve_data = bpy.data.curves.new(name="Polygon", type='CURVE')
        curve_data.dimensions = '3D'
        
        polygon = curve_data.splines.new(type='POLY')
        polygon.points.add(self.sides - 1)
        
        center = Vector(self.start_point)
        radius = (Vector(self.end_point) - center).length
        
        for i in range(self.sides):
            angle = i * (2 * math.pi / self.sides)
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = center.z
            polygon.points[i].co = (x, y, z, 1)
        
        polygon.use_cyclic_u = True

        self.shape_object = bpy.data.objects.new("Polygon", curve_data)
        context.collection.objects.link(self.shape_object)

        # Apply white material
        white_material = get_white_material()
        self.shape_object.data.materials.append(white_material)

class CAD_BIM_OT_CreateDimension(Operator):
    bl_idname = "cad_bim.create_dimension"
    bl_label = "Create Dimension"
    bl_options = {'REGISTER', 'UNDO'}

    start_point: FloatVectorProperty(name="Start Point", default=(0, 0, 0))
    end_point: FloatVectorProperty(name="End Point", default=(0, 0, 0))
    tmp_obj = None
    is_first_point_set = BoolProperty(default=False)

    def modal(self, context, event):
        context.area.tag_redraw()
        
        if event.type == 'MOUSEMOVE':
            current_point = self.get_3d_point(context, event)
            if not self.is_first_point_set:
                self.start_point = current_point
                self.end_point = current_point
            else:
                self.end_point = current_point
            self.update_dimension(context)
        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if not self.is_first_point_set:
                    self.start_point = self.get_3d_point(context, event)
                    self.is_first_point_set = True
                else:
                    self.end_point = self.get_3d_point(context, event)
                    self.create_final_dimension(context)
                    return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_operation(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        set_top_view(context)
        self.is_first_point_set = False
        initial_point = self.get_3d_point(context, event)
        self.start_point = initial_point
        self.end_point = initial_point
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_3d_point(self, context, event):
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        return region_2d_to_location_3d(region, rv3d, coord, Vector((0, 0, 0)))

    def update_dimension(self, context):
        if self.tmp_obj:
            bpy.data.objects.remove(self.tmp_obj, do_unlink=True)
        
        curve_data = bpy.data.curves.new(name="TempDimension", type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new(type='POLY')
        spline.points.add(1)
        spline.points[0].co = (*self.start_point, 1)
        spline.points[1].co = (*self.end_point, 1)

        self.tmp_obj = bpy.data.objects.new("TempDimension", curve_data)
        context.collection.objects.link(self.tmp_obj)

    def create_final_dimension(self, context):
        if self.tmp_obj:
            bpy.data.objects.remove(self.tmp_obj, do_unlink=True)

        start = Vector(self.start_point)
        end = Vector(self.end_point)
        
        curve_data = bpy.data.curves.new(name="Dimension", type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new(type='POLY')
        spline.points.add(1)
        spline.points[0].co = (*start, 1)
        spline.points[1].co = (*end, 1)

        dim_curve = bpy.data.objects.new("Dimension", curve_data)
        context.collection.objects.link(dim_curve)

        # Apply white material to dimension line
        white_material = get_white_material()
        dim_curve.data.materials.append(white_material)
        
        mid_point = (start + end) / 2
        distance = (end - start).length
        
        bpy.ops.object.text_add(location=mid_point)
        text_obj = context.active_object
        text_obj.name = "Dimension_Text"
        text_obj.data.body = f"{distance:.2f}"

        # Apply white material to text
        text_obj.data.materials.append(white_material)
        
        # Calculate rotation to align text with dimension line
        direction = (end - start).normalized()
        up_vector = Vector((0, 0, 1))
        
        # Create a rotation matrix
        rot_matrix = direction.to_track_quat('X', 'Z').to_matrix().to_4x4()
        
        # Apply rotation
        text_obj.matrix_world = rot_matrix @ text_obj.matrix_world
        
        # Adjust text alignment and offset
        text_obj.data.align_x = 'CENTER'
        text_obj.data.align_y = 'CENTER'
        
        # Scale text to a reasonable size
        text_scale = distance * 0.05  # Adjust this factor as needed
        text_obj.scale = (text_scale, text_scale, text_scale)
        
        text_obj.parent = dim_curve

        # Add small lines at the ends of the dimension line
        for point in [start, end]:
            end_line = curve_data.splines.new(type='POLY')
            end_line.points.add(1)
            offset = direction.cross(up_vector) * distance * 0.05
            end_line.points[0].co = (*point - offset, 1)
            end_line.points[1].co = (*point + offset, 1)

        # Ensure the text is on the same plane as the dimension line
        text_obj.location = mid_point


class CAD_BIM_Layer(PropertyGroup):
    name: StringProperty(name="Layer Name")
    visible: BoolProperty(name="Visible", default=True)

class CAD_BIM_OT_AddLayer(Operator):
    bl_idname = "cad_bim.add_layer"
    bl_label = "Add Layer"

    def execute(self, context):
        new_layer = context.scene.cad_bim_layers.add()
        new_layer.name = f"Layer {len(context.scene.cad_bim_layers)}"
        return {'FINISHED'}

class CAD_BIM_OT_RemoveLayer(Operator):
    bl_idname = "cad_bim.remove_layer"
    bl_label = "Remove Layer"

    layer_index: IntProperty()

    def execute(self, context):
        context.scene.cad_bim_layers.remove(self.layer_index)
        return {'FINISHED'}

class CAD_BIM_OT_Extrude(Operator):
    bl_idname = "cad_bim.extrude"
    bl_label = "Extrude 2D to 3D"

    extrude_amount: FloatProperty(name="Extrude Amount", default=1.0, min=0.0)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'CURVE':
                mesh = bpy.data.meshes.new_from_object(obj, preserve_all_data_layers=True, depsgraph=context.evaluated_depsgraph_get())
                new_obj = bpy.data.objects.new(obj.name + "_3D", mesh)
                context.collection.objects.link(new_obj)
                
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bmesh.ops.extrude_face_region(bm, geom=bm.faces[:], vec=(0, 0, self.extrude_amount))
                bm.to_mesh(mesh)
                mesh.update()
                
                bm.free()
        return {'FINISHED'}

class CAD_BIM_PT_Panel(Panel):
    bl_label = "CAD/BIM Tools"
    bl_idname = "CAD_BIM_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CAD/BIM'

    def draw(self, context):
        layout = self.layout
        layout.operator("cad_bim.draw_line", text="Draw Line", icon='GREASEPENCIL')
        layout.operator("cad_bim.draw_rectangle", text="Draw Rectangle", icon='MESH_PLANE')
        layout.operator("cad_bim.draw_circle", text="Draw Circle", icon='MESH_CIRCLE')
        layout.operator("cad_bim.draw_polygon", text="Draw Polygon", icon='MESH_ICOSPHERE')
        layout.operator("cad_bim.create_dimension", text="Create Dimension", icon='DRIVER_DISTANCE')
        layout.operator("cad_bim.extrude", text="Extrude 2D to 3D", icon='MOD_SOLIDIFY')

        layout.separator()
        layout.label(text="Layer Management:")
        for i, layer in enumerate(context.scene.cad_bim_layers):
            row = layout.row()
            row.prop(layer, "name", text="")
            row.prop(layer, "visible", text="")
            row.operator("cad_bim.remove_layer", text="", icon='X').layer_index = i
        layout.operator("cad_bim.add_layer", text="Add Layer", icon='ADD')

classes = (
    CAD_BIM_OT_DrawLine,
    CAD_BIM_OT_DrawRectangle,
    CAD_BIM_OT_DrawCircle,
    CAD_BIM_OT_DrawPolygon,
    CAD_BIM_OT_CreateDimension,
    CAD_BIM_Layer,
    CAD_BIM_OT_AddLayer,
    CAD_BIM_OT_RemoveLayer,
    CAD_BIM_OT_Extrude,
    CAD_BIM_PT_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cad_bim_layers = CollectionProperty(type=CAD_BIM_Layer)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.cad_bim_layers

if __name__ == "__main__":
    register()