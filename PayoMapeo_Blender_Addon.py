bl_info = {
    "name": "PayoMapeo - Red de estaciones (v0.2)",
    "blender": (3, 0, 0),
    "category": "3D View",
    "description": "Crear nodos/estaciones, registrar observaciones, y crear puntos por intersección automática de rayos y segmentos. Creado por el Payocabra",
}

import bpy
from math import radians, degrees, sin, cos, atan2, asin, sqrt, isclose
from mathutils import Vector

# ==========================
# Constantes y Colores
# ==========================
RAY_LENGTH = 1000.0

COLOR_NODO_PRINCIPAL = (0.2, 1.0, 0.2, 1.0)
COLOR_PUNTO = (0.0, 0.4, 0.0, 1.0)
COLOR_RAYO = (0.2, 0.6, 1.0, 1.0)
COLOR_DISTANCIA = (1.0, 0.9, 0.2, 1.0)
# --- NUEVO COLOR ---
COLOR_ALTURA = (0.8, 0.1, 0.8, 1.0) 
COLOR_PROYECCION = (0.2, 0.8, 1.0, 1.0)  # texto de proyección al suelo

# ==========================
# Utilidades
# ==========================

def set_object_color(obj, color):
    """Establece el color de un objeto directamente. Ideal para Empties y el modo 'Object Color'."""
    obj.color = color

def apply_material(obj, color, mat_name_prefix="Topo_Mat"):
    """Crea y aplica un material con un color específico. Ideal para texto y mallas."""
    mat_name = f"{mat_name_prefix}_{int(color[0]*255)}_{int(color[1]*255)}_{int(color[2]*255)}"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = False
        mat.diffuse_color = color
    
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    set_object_color(obj, color)

def ensure_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col

LINE_TYPES = {"rayo_observacion", "observacion_segmento"}
def is_line_object(obj):
    return obj.type == 'MESH' and obj.get("tipo") in LINE_TYPES

def nodes_enum_items(self, context):
    items = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.get("tipo") in {"nodo", "punto"}]
    return items if items else [("NONE", "Ninguna", "No hay nodos/estaciones")]

def deg2rad(a): return radians(a)
def rad2deg(a): return degrees(a)
def wrap_angle_deg(a): a = a % 360.0; return a + 360.0 if a < 0 else a
def dir_from_az_inc(az_deg, inc_deg): az, inc = deg2rad(az_deg), deg2rad(inc_deg); return Vector((cos(inc) * cos(az), cos(inc) * sin(az), sin(inc)))
def closest_point_between_rays(P1, v1, P2, v2):
    w0 = Vector(P1) - Vector(P2)
    a, b, c = v1.dot(v1), v1.dot(v2), v2.dot(v2)
    d, e = v1.dot(w0), v2.dot(w0)
    den = a * c - b * b
    if abs(den) < 1e-9: return None, w0.cross(v2).length, None, None
    t1 = (b * e - c * d) / den
    t2 = (a * e - b * d) / den
    C1 = Vector(P1) + t1 * v1
    C2 = Vector(P2) + t2 * v2
    return tuple((C1 + C2) / 2.0), (C1 - C2).length, t1, t2

# ==========================
# Lógica de Creación y Geometría
# ==========================

def _create_text_object(name, body, location, collection, scale=0.3, tipo="texto_info", color=None):
    txt_data = bpy.data.curves.new(name=name, type='FONT')
    txt_obj = bpy.data.objects.new(name, txt_data)
    txt_data.body = body
    txt_obj.location = location
    txt_obj.scale = (scale, scale, scale)
    txt_obj["tipo"] = tipo
    if color:
        apply_material(txt_obj, color)
    collection.objects.link(txt_obj)
    return txt_obj

def _create_intersection_assets(context, A, B, M, gap, dist_A, dist_B, point_name):
    # --- MODIFICADO: USA LA POSICIÓN REAL DEL NODO, NO EL PUNTO DE VISIÓN ---
    loc_A = bpy.data.objects[A.name].location
    loc_B = bpy.data.objects[B.name].location
    
    col_new = ensure_collection(point_name)
    node = bpy.data.objects.new(point_name, None)
    node.empty_display_type = 'SPHERE'
    node.empty_display_size = 0.4
    node.location = M
    set_object_color(node, COLOR_PUNTO)
    node["tipo"] = "punto"
    node["gap_interseccion"] = gap
    col_new.objects.link(node)
    
    col_A, col_B = ensure_collection(A.name), ensure_collection(B.name)
    
    # De A a M
    mesh_A = bpy.data.meshes.new(f"Seg_{A.name}_{node.name}")
    line_A = bpy.data.objects.new(mesh_A.name, mesh_A)
    mesh_A.from_pydata([loc_A, node.location], [(0,1)], [])
    apply_material(line_A, COLOR_DISTANCIA)
    col_A.objects.link(line_A)
    mid_A = (Vector(loc_A) + Vector(M)) / 2.0
    _create_text_object(f"dist_{A.name}_{node.name}", f"{dist_A:.2f} m", mid_A, col_A, 0.9, "texto_distancia", COLOR_DISTANCIA)

    # De B a M
    mesh_B = bpy.data.meshes.new(f"Seg_{B.name}_{node.name}")
    line_B = bpy.data.objects.new(mesh_B.name, mesh_B)
    mesh_B.from_pydata([loc_B, node.location], [(0,1)], [])
    apply_material(line_B, COLOR_DISTANCIA)
    col_B.objects.link(line_B)
    mid_B = (Vector(loc_B) + Vector(M)) / 2.0
    _create_text_object(f"dist_{B.name}_{node.name}", f"{dist_B:.2f} m", mid_B, col_B, 0.9, "texto_distancia", COLOR_DISTANCIA)
    
    return node

def _check_intersections(context, new_line_obj):
    # --- MODIFICADO: CALCULA EL PUNTO DE PARTIDA REAL (CON ALTURA) ---
    origin_obj1 = bpy.data.objects[new_line_obj["origen"]]
    height1 = new_line_obj.get("observer_height", 0.0)
    P1 = origin_obj1.location + Vector((0, 0, height1))
    v1 = Vector(new_line_obj["vector"])
    tipo1 = new_line_obj["tipo"]
    len1 = v1.length if tipo1 == "observacion_segmento" else RAY_LENGTH
    
    all_lines = [obj for obj in bpy.data.objects if is_line_object(obj) and obj != new_line_obj]
    
    for other_line in all_lines:
        origin_obj2 = bpy.data.objects[other_line["origen"]]
        height2 = other_line.get("observer_height", 0.0)
        P2 = origin_obj2.location + Vector((0, 0, height2))
        v2 = Vector(other_line["vector"])
        tipo2 = other_line["tipo"]
        len2 = v2.length if tipo2 == "observacion_segmento" else RAY_LENGTH

        M, gap, t1, t2 = closest_point_between_rays(P1, v1.normalized(), P2, v2.normalized())
        
        if M is not None and gap < context.scene.topo_intersection_margin:
            t1_valid = (tipo1 == "rayo_observacion" and t1 >= -1e-6) or (tipo1 == "observacion_segmento" and -1e-6 <= t1 <= len1 + 1e-6)
            t2_valid = (tipo2 == "rayo_observacion" and t2 >= -1e-6) or (tipo2 == "observacion_segmento" and -1e-6 <= t2 <= len2 + 1e-6)
            
            if t1_valid and t2_valid:
                orig_A = bpy.data.objects[new_line_obj["origen"]]
                orig_B = bpy.data.objects[other_line["origen"]]
                point_name = f"Int_{orig_A.name}_{orig_B.name}"
                # Pasamos los objetos de origen, no los puntos de visión
                node = _create_intersection_assets(context, orig_A, orig_B, M, gap, t1, t2, point_name)
                print(f"Intersección válida encontrada. Punto '{node.name}' creado.")

# ==========================
# Operadores
# ==========================

class TOPO_OT_add_node(bpy.types.Operator):
    bl_idname = "topo.add_node"
    bl_label = "Añadir nodo/estación"
    name: bpy.props.StringProperty(name="Nombre", default="Nodo")
    def execute(self, context):
        col = ensure_collection(self.name)
        empty = bpy.data.objects.new(self.name, None)
        empty.empty_display_size = 0.5
        empty.empty_display_type = 'SPHERE'
        set_object_color(empty, COLOR_NODO_PRINCIPAL)
        empty["tipo"] = "nodo"
        col.objects.link(empty)
        context.scene.topo_active_origin = empty.name
        self.report({'INFO'}, f"Nodo '{self.name}' creado")
        return {'FINISHED'}

class TOPO_OT_add_node_from_obs(bpy.types.Operator):
    bl_idname = "topo.add_node_from_obs"
    bl_label = "Nuevo punto desde observación"
    origin: bpy.props.EnumProperty(name="Origen", items=nodes_enum_items)
    point_name: bpy.props.StringProperty(name="Nombre del punto", default="Punto")
    azimuth: bpy.props.FloatProperty(name="Acimut (°)", default=0.0)
    inclination: bpy.props.FloatProperty(name="Inclinación (°)", default=0.0)
    distance: bpy.props.FloatProperty(name="Distancia (m)", default=10.0, min=0.0)
    # --- NUEVA PROPIEDAD ---
    observer_height: bpy.props.FloatProperty(name="Altura Observador (m)", default=0.0, min=0.0)

    def execute(self, context):
        origin_obj = bpy.data.objects.get(self.origin)
        if not origin_obj: return {'CANCELLED'}
        az = self.azimuth + (context.scene.topo_declination if context.scene.topo_use_declination else 0.0)
        v = dir_from_az_inc(az, self.inclination)
        col = ensure_collection(origin_obj.name)

        # --- LÓGICA MODIFICADA: USAR ALTURA DEL OBSERVADOR ---
        feet_pos = origin_obj.location
        eye_pos = feet_pos + Vector((0, 0, self.observer_height))

        # --- LÓGICA NUEVA: DIBUJAR LÍNEA DE ALTURA SI ES NECESARIO ---
        if self.observer_height > 0.0:
            # Crear línea vertical
            mesh_h = bpy.data.meshes.new(f"Altura_{origin_obj.name}")
            line_h = bpy.data.objects.new(mesh_h.name, mesh_h)
            mesh_h.from_pydata([feet_pos, eye_pos], [(0,1)], [])
            apply_material(line_h, COLOR_ALTURA)
            col.objects.link(line_h)
            # Crear texto de altura
            mid_h = (feet_pos + eye_pos) / 2.0
            text_h = _create_text_object(f"h_val_{origin_obj.name}", f"{self.observer_height:.2f} m", mid_h, col, 0.4, "texto_altura", COLOR_ALTURA)
	    # --- ROTAR 90° en el eje X ---
            text_h.rotation_euler[0] = radians(90)
        
        if isclose(self.distance, 0.0, abs_tol=1e-6): # Crear Rayo
            far_point = eye_pos + RAY_LENGTH * v
            mesh = bpy.data.meshes.new(f"Rayo_{origin_obj.name}")
            ray_obj = bpy.data.objects.new(mesh.name, mesh)
            mesh.from_pydata([eye_pos, far_point], [(0,1)], [])
            ray_obj["tipo"] = "rayo_observacion"
            ray_obj["origen"] = origin_obj.name
            ray_obj["vector"] = v
            ray_obj["observer_height"] = self.observer_height # Guardar altura
            apply_material(ray_obj, COLOR_RAYO)
            col.objects.link(ray_obj)
            _check_intersections(context, ray_obj)
        else: # Crear Punto y Segmento
            d = self.distance
            new_loc = eye_pos + d * v
            new_col = ensure_collection(self.point_name)
            node = bpy.data.objects.new(self.point_name, None)
            node.empty_display_type = 'ARROWS'
            node.empty_display_size = 0.3
            node.location = new_loc
            set_object_color(node, COLOR_PUNTO)
            node["tipo"] = "punto"
            new_col.objects.link(node)

            mesh = bpy.data.meshes.new(f"Obs_{origin_obj.name}_{node.name}")
            line = bpy.data.objects.new(mesh.name, mesh)
            mesh.from_pydata([eye_pos, node.location], [(0,1)], [])
            line["tipo"] = "observacion_segmento"
            line["origen"] = origin_obj.name
            line["destino"] = node.name # Guardar destino para la proyección
            line["vector"] = Vector(node.location) - eye_pos
            line["observer_height"] = self.observer_height # Guardar altura
            line["is_projected"] = False # Marcar como no proyectada
            apply_material(line, COLOR_DISTANCIA)
            col.objects.link(line)
            
            mid = (eye_pos + Vector(node.location)) / 2.0
            dist_text = _create_text_object(f"dist_{origin_obj.name}_{node.name}", f"{d:.2f} m", mid, col, 0.9, "texto_distancia", COLOR_DISTANCIA)
            
            # --- NUEVO: GUARDAR REFERENCIAS PARA BORRAR AL PROYECTAR ---
            line["dist_texto"] = dist_text.name
            if self.observer_height > 0.0:
                line["altura_viz_linea"] = line_h.name
                line["altura_viz_texto"] = text_h.name
            
            _check_intersections(context, line)
            
        return {'FINISHED'}

# --- OPERADOR COMPLETAMENTE NUEVO ---
class TOPO_OT_project_to_ground(bpy.types.Operator):
    """Proyecta una observación con altura de observador al suelo."""
    bl_idname = "topo.project_to_ground"
    bl_label = "Proyectar al Suelo"
    bl_options = {'REGISTER', 'UNDO'}

    borrar_originales: bpy.props.BoolProperty(
        name="Borrar originales",
        description="Eliminar la línea y textos de la observación con altura",
        default=True
    )

    @classmethod
    def poll(cls, context):
        # Puedes personalizar la condición según tu lógica
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        line_obj = context.active_object
        origin_name = line_obj["origen"]
        target_name = line_obj["destino"]
        origin_obj = bpy.data.objects.get(origin_name)
        target_obj = bpy.data.objects.get(target_name)
        
        if not origin_obj or not target_obj:
            self.report({'WARNING'}, "No se encontraron el origen o el destino.")
            return {'CANCELLED'}

        feet_pos = origin_obj.location
        target_pos = target_obj.location
        new_dist = (target_pos - feet_pos).length
        col = ensure_collection(origin_name)
        
        # Nueva línea proyectada
        mesh = bpy.data.meshes.new(f"Proy_{origin_name}_{target_name}")
        new_line = bpy.data.objects.new(mesh.name, mesh)
        mesh.from_pydata([feet_pos, target_pos], [(0,1)], [])
        new_line["tipo"] = "observacion_segmento"
        new_line["origen"] = origin_name
        new_line["destino"] = target_name
        new_line["observer_height"] = 0.0
        new_line["is_projected"] = True
        apply_material(new_line, COLOR_PROYECCION)
        col.objects.link(new_line)
        
        # Texto de distancia
        mid = (feet_pos + target_pos) / 2.0
        new_text = _create_text_object(f"dist_proy_{origin_name}_{target_name}", f"{new_dist:.2f} m", mid, col, 1.2, "texto_proyeccion", COLOR_PROYECCION)
        new_line["dist_texto"] = new_text.name

        # Solo borrar si está activado el checkbox
        if self.borrar_originales:
            objs_to_delete = [line_obj]
            for prop_name in ["dist_texto", "altura_viz_linea", "altura_viz_texto"]:
                if prop_name in line_obj:
                    obj = bpy.data.objects.get(line_obj[prop_name])
                    if obj:
                        objs_to_delete.append(obj)
            for obj in objs_to_delete:
                bpy.data.objects.remove(obj, do_unlink=True)

        self.report({'INFO'}, f"Observación proyectada al suelo.")
        bpy.context.view_layer.objects.active = new_line
        return {'FINISHED'}


# ==========================
# Paneles
# ==========================
class TOPO_PT_panel(bpy.types.Panel):
    bl_label = "PayoMapeo"
    bl_idname = "TOPO_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Topografía'
    def draw(self, context):
        s = context.scene
        layout = self.layout
        box = layout.box()
        box.label(text="Opciones generales")
        row = box.row(align=True)
        row.prop(s, "topo_use_declination", text="Usar declinación")
        row.prop(s, "topo_declination")
        box.prop(s, "topo_intersection_margin")
        box = layout.box()
        box.label(text="Nodos / estaciones")
        box.operator("topo.add_node", icon='EMPTY_AXIS')
        box = layout.box()
        box.label(text="Nuevo punto desde observación")
        box.label(text="Poner Distancia=0 para crear rayo 'infinito'", icon='INFO')
        col = box.column(align=True)
        col.prop(s, "topo_active_origin", text="Origen")
        col.prop(s, "topo_new_point_name", text="Nombre")
        col.prop(s, "topo_azimuth", text="Acimut (°)")
        col.prop(s, "topo_inclination", text="Inclinación (°)")
        col.prop(s, "topo_distance", text="Distancia (m)")
        # --- NUEVO CAMPO EN LA INTERFAZ ---
        col.prop(s, "topo_observer_height", text="Altura Obs. (m)")
        
        op = col.operator("topo.add_node_from_obs", icon='OUTLINER_OB_EMPTY')
        op.origin = s.topo_active_origin
        op.point_name = s.topo_new_point_name
        op.azimuth = s.topo_azimuth
        op.inclination = s.topo_inclination
        op.distance = s.topo_distance
        op.observer_height = s.topo_observer_height

# ==========================
# Operador NUEVO: Crear línea manual
# ==========================
class TOPO_OT_create_manual_line(bpy.types.Operator):
    """Crea una línea entre dos nodos/puntos seleccionados y muestra su distancia"""
    bl_idname = "topo.create_manual_line"
    bl_label = "Crear línea manual"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Requiere exactamente 2 objetos seleccionados que sean nodo o punto
        sel = [obj for obj in context.selected_objects if obj.get("tipo") in {"nodo", "punto"}]
        return len(sel) == 2

    def execute(self, context):
        sel = [obj for obj in context.selected_objects if obj.get("tipo") in {"nodo", "punto"}]
        if len(sel) != 2:
            self.report({'WARNING'}, "Debes seleccionar exactamente 2 nodos o puntos.")
            return {'CANCELLED'}

        A, B = sel
        loc_A, loc_B = A.location, B.location
        dist = (loc_B - loc_A).length

        # Crear la línea
        mesh = bpy.data.meshes.new(f"Linea_{A.name}_{B.name}")
        line_obj = bpy.data.objects.new(mesh.name, mesh)
        mesh.from_pydata([loc_A, loc_B], [(0, 1)], [])
        line_obj["tipo"] = "linea_manual"
        apply_material(line_obj, COLOR_DISTANCIA)
        col = ensure_collection("Lineas_Manual")
        col.objects.link(line_obj)

        # Texto de distancia
        mid = (loc_A + loc_B) / 2.0
        _create_text_object(f"dist_{A.name}_{B.name}", f"{dist:.2f} m", mid, col, 0.9, "texto_distancia", COLOR_DISTANCIA)

        self.report({'INFO'}, f"Línea manual creada entre {A.name} y {B.name}. Distancia: {dist:.2f} m")
        return {'FINISHED'}


# ==========================
# Panel NUEVO: Herramientas de líneas manuales
# ==========================
class TOPO_PT_manual_lines(bpy.types.Panel):
    bl_label = "Líneas Manuales"
    bl_idname = "TOPO_PT_manual_lines"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Topografía'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Selecciona 2 nodos/puntos")
        box.operator("topo.create_manual_line", icon='MESH_DATA')


# --- PANEL ACCIONES ---
class TOPO_PT_selection_panel(bpy.types.Panel):
    bl_label = "Acciones de Observación"
    bl_idname = "TOPO_PT_selection_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Topografía'
    
    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text=f"Observación: {context.active_object.name}")

        # Aviso para el usuario
        box.label(
            text="Sólo líneas con DISTANCIA definida!",
            icon='INFO'
        )
        
        # Solo el botón, SIN el checkbox redundante
        box.operator("topo.project_to_ground", icon='TRIA_DOWN_BAR')


classes = [
    TOPO_OT_add_node, 
    TOPO_OT_add_node_from_obs,
    TOPO_OT_project_to_ground, # Añadir nuevo operador
    TOPO_PT_panel,
    TOPO_PT_selection_panel, # Añadir nuevo panel
    TOPO_OT_create_manual_line,   # <--- NUEVO
    TOPO_PT_manual_lines   
]
def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.topo_use_declination = bpy.props.BoolProperty(name="Usar declinación", default=False)
    bpy.types.Scene.topo_declination = bpy.props.FloatProperty(name="Declinación (°)", default=0.0)
    bpy.types.Scene.topo_intersection_margin = bpy.props.FloatProperty(name="Margen de Intersección (m)", default=0.1, min=0.001, soft_max=5.0, step=0.1, precision=3)
    bpy.types.Scene.topo_active_origin = bpy.props.EnumProperty(name="Origen", items=nodes_enum_items)
    bpy.types.Scene.topo_new_point_name = bpy.props.StringProperty(name="Nombre punto", default="Punto")
    bpy.types.Scene.topo_azimuth = bpy.props.FloatProperty(name="Acimut (°)", default=0.0)
    bpy.types.Scene.topo_inclination = bpy.props.FloatProperty(name="Inclinación (°)", default=0.0)
    bpy.types.Scene.topo_distance = bpy.props.FloatProperty(name="Distancia (m)", default=10.0, min=0.0)
    # --- NUEVA PROPIEDAD DE ESCENA ---
    bpy.types.Scene.topo_observer_height = bpy.props.FloatProperty(name="Altura Observador (m)", default=0.0, min=0.0)

def unregister():
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    del bpy.types.Scene.topo_use_declination; del bpy.types.Scene.topo_declination
    del bpy.types.Scene.topo_intersection_margin; del bpy.types.Scene.topo_active_origin
    del bpy.types.Scene.topo_new_point_name; del bpy.types.Scene.topo_azimuth
    del bpy.types.Scene.topo_inclination; del bpy.types.Scene.topo_distance
    # --- BORRAR NUEVA PROPIEDAD ---
    del bpy.types.Scene.topo_observer_height

if __name__ == "__main__":
    register()