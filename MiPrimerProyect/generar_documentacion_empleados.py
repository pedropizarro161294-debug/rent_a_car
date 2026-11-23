from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "documentacion"
OUTPUT_DIR.mkdir(exist_ok=True)
DIAGRAM_PATH = OUTPUT_DIR / "bpmn_gestion_empleados.png"
DOCX_PATH = OUTPUT_DIR / "Empleados_Perfiles_Permisos_BPMN.docx"


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    path = candidates[0]
    if not Path(path).exists():
        path = candidates[1]
    return ImageFont.truetype(path, size) if Path(path).exists() else ImageFont.load_default()


def crear_bpmn():
    width, height = 1500, 940
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle((40, 40, 1460, 900), fill="#F7F9FC", outline="#7A8796", width=2)
    draw.rectangle((40, 40, 260, 900), fill="#E8EFF7", outline="#7A8796", width=2)
    draw.rectangle((260, 40, 1460, 250), fill="#FFFFFF", outline="#7A8796", width=2)
    draw.rectangle((260, 250, 1460, 470), fill="#FFFFFF", outline="#7A8796", width=2)
    draw.rectangle((260, 470, 1460, 690), fill="#FFFFFF", outline="#7A8796", width=2)
    draw.rectangle((260, 690, 1460, 900), fill="#FFFFFF", outline="#7A8796", width=2)

    draw.text((75, 145), "Administrador", fill="#1F2937", font=font(24, True))
    draw.text((75, 350), "Empleado", fill="#1F2937", font=font(24, True))
    draw.text((75, 560), "Sistema", fill="#1F2937", font=font(24, True))
    draw.text((75, 770), "BD / Django", fill="#1F2937", font=font(24, True))

    def box(x1, y1, x2, y2, text, fill="#DCEBFA", border="#3973A8"):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=12, fill=fill, outline=border, width=3)
        lines = text.split("\n")
        y = y1 + (y2 - y1 - len(lines) * 23) // 2
        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font(18))
            tw = bb[2] - bb[0]
            draw.text((x1 + (x2 - x1 - tw) // 2, y), line, fill="#111827", font=font(18))
            y += 25

    def diamond(cx, cy, text):
        points = [(cx, cy - 38), (cx + 45, cy), (cx, cy + 38), (cx - 45, cy)]
        draw.polygon(points, fill="#FFF1C7", outline="#A96D00")
        bb = draw.textbbox((0, 0), text, font=font(16, True))
        tw = bb[2] - bb[0]
        draw.text((cx - tw // 2, cy - 12), text, fill="#111827", font=font(16, True))

    def arrow(x1, y1, x2, y2):
        draw.line((x1, y1, x2, y2), fill="#374151", width=3)
        draw.polygon([(x2, y2), (x2 - 12, y2 - 7), (x2 - 12, y2 + 7)], fill="#374151")

    draw.ellipse((280, 125, 320, 165), fill="#D1FAE5", outline="#047857", width=3)
    box(350, 100, 540, 190, "Ingresar al\nsistema")
    diamond(590, 145, "¿Valido?")
    box(680, 100, 890, 190, "Seleccionar acción\nAlta / Modificar / Baja")
    diamond(940, 145, "Permiso")
    box(990, 100, 1180, 190, "Django ejecuta\nvista protegida")
    box(1230, 100, 1410, 190, "Actualizar\nempleado")

    box(350, 300, 540, 390, "Ingresar usuario\ny clave")
    diamond(590, 345, "¿Activo?")
    box(680, 300, 870, 390, "Cambiar clave\nsi es temporal")
    box(350, 520, 540, 610, "Validar credenciales")
    box(680, 520, 870, 610, "Consultar perfil\ny permisos")
    box(990, 520, 1180, 610, "Generar usuario /\nclave temporal")
    box(1230, 520, 1410, 610, "Mostrar solo\nresultado autorizado")

    box(350, 735, 540, 825, "Buscar empleado\npor tabla Empleados")
    box(680, 735, 870, 825, "Alta: crear cuenta")
    box(990, 735, 1180, 825, "Modificar: correo\nactualiza fecha")
    box(1230, 735, 1410, 825, "Baja: ACTIVO=No\n+ FECHA_BAJA")

    arrow(320, 145, 350, 145)
    arrow(540, 145, 545, 145)
    arrow(635, 145, 680, 145)
    arrow(890, 145, 895, 145)
    arrow(985, 145, 990, 145)
    arrow(1180, 145, 1230, 145)
    arrow(445, 190, 445, 300)
    arrow(540, 345, 545, 345)
    arrow(635, 345, 680, 345)
    arrow(445, 390, 445, 520)
    arrow(540, 565, 680, 565)
    arrow(870, 565, 990, 565)
    arrow(1180, 565, 1230, 565)
    arrow(445, 610, 445, 735)
    arrow(540, 780, 680, 780)
    arrow(870, 780, 990, 780)
    arrow(1180, 780, 1230, 780)

    draw.ellipse((1200, 850, 1240, 890), fill="#111827")
    draw.ellipse((1206, 856, 1234, 884), fill="#111827")

    image.save(DIAGRAM_PATH)


def set_cell_text(cell, text, bold=False, color=None):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def crear_word():
    crear_bpmn()
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    title = doc.add_heading("Sistema de Gestión de Empleados", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph("Perfiles, permisos y proceso BPMN del sistema desarrollado con Django")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].bold = True

    doc.add_heading("1. Alcance", level=1)
    doc.add_paragraph(
        "Este documento describe la administración unificada de empleados dentro del proyecto "
        "Rent a Car desarrollado con el framework Django. La tabla Empleados concentra los "
        "datos personales, laborales y de acceso necesarios para la autenticación y la seguridad."
    )

    doc.add_heading("2. Modelo de seguridad", level=1)
    doc.add_paragraph(
        "La seguridad se organiza mediante tres entidades: Perfil, Permiso y Perfil-Permiso "
        "(tabla intermedia). Cada empleado pertenece a un perfil y recibe únicamente las acciones "
        "que ese perfil tiene asociadas."
    )

    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    headers = ["Entidad", "Atributos principales", "Función"]
    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, bold=True)

    filas = [
        ("Perfil", "ID_PERFIL, NOMBRE_PERFIL, DESCRIPCION", "Agrupa los niveles de acceso."),
        ("Permiso", "ID_PERMISO, NOMBRE_PERMISO, DESCRIPCION", "Define una acción autorizada."),
        ("Perfil-Permiso", "ID_PERFIL, ID_PERMISO", "Relaciona perfiles con permisos."),
        ("Empleado", "DNI, nombre, apellido, correo, usuario, clave, ACTIVO, perfil, fecha baja", "Contiene cuenta y datos del empleado."),
    ]
    for entidad, atributos, funcion in filas:
        cells = table.add_row().cells
        set_cell_text(cells[0], entidad, bold=True)
        set_cell_text(cells[1], atributos)
        set_cell_text(cells[2], funcion)

    doc.add_heading("3. Matriz Perfil-Permiso", level=1)
    matrix = doc.add_table(rows=1, cols=3)
    matrix.alignment = WD_TABLE_ALIGNMENT.CENTER
    matrix.style = "Table Grid"
    for index, header in enumerate(["Permiso", "Administrador", "Empleado"]):
        set_cell_text(matrix.rows[0].cells[index], header, bold=True)

    permisos = [
        ("usuarios.ver", "Sí", "No"),
        ("usuarios.alta", "Sí", "No"),
        ("usuarios.modificar", "Sí", "No"),
        ("usuarios.baja", "Sí", "No"),
        ("usuarios.restablecer_clave", "Sí", "No"),
        ("empleados.ver", "Sí", "Sí"),
        ("empleados.gestionar", "Sí", "No"),
    ]
    for permiso, administrador, empleado in permisos:
        cells = matrix.add_row().cells
        set_cell_text(cells[0], permiso)
        set_cell_text(cells[1], administrador, bold=administrador == "Sí")
        set_cell_text(cells[2], empleado, bold=empleado == "Sí")

    doc.add_heading("4. Flujo BPMN", level=1)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DIAGRAM_PATH), width=Inches(7))

    doc.add_heading("5. Descripción detallada del proceso", level=1)
    pasos = [
        ("Inicio", "El usuario accede a la pantalla de inicio de sesión."),
        ("Autenticación", "El sistema busca el nombre de usuario en Empleados y verifica la clave cifrada."),
        ("Control de acceso", "Si el empleado está ACTIVO, se cargan su perfil y permisos en la sesión."),
        ("Cambio obligatorio", "Si DEBE_CAMBIAR_CLAVE es verdadero, se exige una contraseña nueva antes de continuar."),
        ("Consulta", "Con empleados.ver se puede abrir el panel y filtrar empleados."),
        ("Alta", "Con empleados.gestionar se crean los datos personales y se asigna el perfil; el sistema genera usuario y clave temporal."),
        ("Modificación", "El formulario de modificación solo permite cambiar el correo. FECHA_ULTIMA_MODIFICACION se actualiza automáticamente."),
        ("Baja", "Con empleados.gestionar se cambia ACTIVO a No y se registra FECHA_BAJA automáticamente."),
        ("Reactivación", "El empleado puede volver a ACTIVO y la fecha de baja se limpia."),
        ("Restablecimiento", "Con usuarios.restablecer_clave se genera una clave temporal cifrada y se exige cambiarla en el próximo login."),
        ("Fin", "El sistema mantiene el historial del empleado sin eliminarlo físicamente."),
    ]
    for etapa, descripcion in pasos:
        paragraph = doc.add_paragraph()
        paragraph.style = "List Number"
        run = paragraph.add_run(etapa + ": ")
        run.bold = True
        paragraph.add_run(descripcion)

    doc.add_heading("6. Reglas BPMN y excepciones", level=1)
    reglas = [
        "Un empleado inactivo no puede iniciar sesión.",
        "Un empleado no puede darse de baja a sí mismo.",
        "El usuario se genera automáticamente a partir del apellido y la primera letra del nombre.",
        "Las claves se almacenan mediante hash; no se guarda la clave temporal en texto plano.",
        "La modificación no puede cambiar DNI, nombre, apellido, fecha de alta ni perfil.",
        "El perfil Administrador concentra todos los permisos registrados.",
        "El perfil Empleado solamente puede ver el listado de empleados.",
        "Las altas y restablecimientos exigen cambiar la clave temporal en el próximo ingreso.",
    ]
    for regla in reglas:
        doc.add_paragraph(regla, style="List Bullet")

    doc.add_heading("7. Campos relevantes de Empleados", level=1)
    campos = [
        ("DNI", "Identificación principal del empleado."),
        ("NOMBRE", "Nombre del empleado."),
        ("APELLIDO", "Apellido del empleado."),
        ("CORREO", "Correo modificable desde la función de modificación."),
        ("NOMBRE_USUARIO", "Usuario generado automáticamente."),
        ("CLAVE", "Hash de la contraseña."),
        ("ACTIVO", "SI: cuenta activa; NO: cuenta dada de baja."),
        ("DEBE_CAMBIAR_CLAVE", "Obliga el cambio de clave después de alta o restablecimiento."),
        ("FECHA_ALTA", "Fecha de incorporación."),
        ("FECHA_ULTIMA_MODIFICACION", "Se actualiza automáticamente al modificar el correo."),
        ("FECHA_BAJA", "Se carga automáticamente al realizar la baja."),
        ("ID_PERFIL", "Perfil de seguridad asignado al empleado."),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    set_cell_text(table.rows[0].cells[0], "Campo", bold=True)
    set_cell_text(table.rows[0].cells[1], "Uso", bold=True)
    for campo, uso in campos:
        cells = table.add_row().cells
        set_cell_text(cells[0], campo)
        set_cell_text(cells[1], uso)

    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Proyecto Rent a Car - Sistema de Usuarios y Empleados")

    doc.save(DOCX_PATH)
    print(DOCX_PATH)


if __name__ == "__main__":
    crear_word()
