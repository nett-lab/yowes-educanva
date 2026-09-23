"""
Argentina data and document generators

Argentine teacher verification requirements:
1. Payment Slip (Recibo de Sueldo)
2. Employment Certificate (Certificado de Trabajo)
3. Signed School Letter (Carta Institucional)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar, load_font
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import random


# Argentina K-12 Schools Database (Nivel Inicial, Primario y Secundario)
DEFAULT_ARGENTINA_SCHOOLS = [
    {"name": "Colegio Amancay", "address": "Av. Bustillo Km 9.500", "city": "San Carlos de Bariloche", "province": "Río Negro", "postcode": "R8400", "phone": "+54 294 446-1500", "domain": "colegioamancay.edu.ar"},
    {"name": "Colegio Los Robles", "address": "Camino Real 1234", "city": "Pilar", "province": "Buenos Aires", "postcode": "B1629", "phone": "+54 230 466-3000", "domain": "losrobles.edu.ar"},
    {"name": "Colegio Northlands", "address": "Roma 1248", "city": "Olivos", "province": "Buenos Aires", "postcode": "B1636", "phone": "+54 11 4711-8400", "domain": "northlands.edu.ar"},
    {"name": "Colegio San Patricio", "address": "Av. del Libertador 5050", "city": "Ciudad de Buenos Aires", "province": "CABA", "postcode": "C1426", "phone": "+54 11 4773-2400", "domain": "sanpatricio.edu.ar"},
    {"name": "Colegio Las Cumbres", "address": "Av. Pedro Goyena 425", "city": "Ciudad de Buenos Aires", "province": "CABA", "postcode": "C1424", "phone": "+54 11 4922-1100", "domain": "lascumbres.edu.ar"},
    {"name": "Colegio Tarbut", "address": "Don Bosco 4221", "city": "Olivos", "province": "Buenos Aires", "postcode": "B1636", "phone": "+54 11 4794-7500", "domain": "tarbut.edu.ar"},
    {"name": "Colegio del Sol", "address": "Sucre 3338", "city": "Ciudad de Buenos Aires", "province": "CABA", "postcode": "C1428", "phone": "+54 11 4544-7300", "domain": "colegiodelsol.edu.ar"},
    {"name": "Colegio Lincoln", "address": "Andrés Ferreyra 4073", "city": "La Lucila", "province": "Buenos Aires", "postcode": "B1637", "phone": "+54 11 4851-1700", "domain": "lincoln.edu.ar"},
    {"name": "Colegio San Jorge Norte", "address": "Las Magnolias 750", "city": "Los Polvorines", "province": "Buenos Aires", "postcode": "B1613", "phone": "+54 11 4663-3800", "domain": "sanjorgenorte.edu.ar"},
    {"name": "Colegio Mark Twain", "address": "Carlos F. Melo 3030", "city": "Olivos", "province": "Buenos Aires", "postcode": "B1636", "phone": "+54 11 4790-1234", "domain": "marktwain.edu.ar"},
    {"name": "Colegio Cardenal Newman", "address": "Av. del Libertador 17115", "city": "Beccar", "province": "Buenos Aires", "postcode": "B1643", "phone": "+54 11 4747-0300", "domain": "newman.edu.ar"},
    {"name": "Colegio San Andrés", "address": "Roque Sáenz Peña 601", "city": "Olivos", "province": "Buenos Aires", "postcode": "B1636", "phone": "+54 11 4711-8000", "domain": "sanandres.edu.ar"},
    {"name": "Colegio Tomás Alva Edison", "address": "Av. Cabildo 1175", "city": "Ciudad de Buenos Aires", "province": "CABA", "postcode": "C1426", "phone": "+54 11 4783-2200", "domain": "edison.edu.ar"},
    {"name": "Colegio Esquiú", "address": "Mariano Acosta 555", "city": "Córdoba", "province": "Córdoba", "postcode": "X5000", "phone": "+54 351 421-8800", "domain": "esquiu.edu.ar"},
    {"name": "Colegio Tomás Moro", "address": "Independencia 458", "city": "Mendoza", "province": "Mendoza", "postcode": "M5500", "phone": "+54 261 425-9900", "domain": "tomasmoro.edu.ar"},
]

# Argentine Names
ARGENTINA_FIRST_NAMES = [
    "Juan", "María", "Carlos", "Ana", "José", "Laura", "Diego", "Sofía",
    "Martín", "Lucía", "Mateo", "Valentina", "Santiago", "Catalina", "Nicolás", "Florencia",
    "Facundo", "Martina", "Tomás", "Camila", "Franco", "Victoria", "Lucas", "Agustina",
    "Joaquín", "Julieta", "Benjamín", "Emma", "Manuel", "Isabella", "Sebastián", "Milagros"
]

ARGENTINA_LAST_NAMES = [
    "González", "Rodríguez", "Fernández", "García", "Martínez", "López", "Pérez", "Sánchez",
    "Romero", "Díaz", "Torres", "Álvarez", "Ruiz", "Ramírez", "Flores", "Benítez",
    "Medina", "Castro", "Morales", "Ortiz", "Silva", "Rojas", "Giménez", "Pereyra",
    "Acosta", "Molina", "Vargas", "Aguirre", "Cabrera", "Vega", "Herrera", "Domínguez"
]

# Argentine K-12 Teaching Positions (Nivel Inicial, Primario, Secundario)
ARGENTINA_TEACHING_POSITIONS = [
    "Maestra Jardinera",
    "Docente de Nivel Inicial",
    "Maestro/a de Grado",
    "Maestro/a de Nivel Primario",
    "Profesor/a de Educación Física - Primaria",
    "Profesor/a de Inglés - Primaria",
    "Profesor/a de Música - Primaria",
    "Profesor/a de Plástica - Primaria",
    "Profesor/a de Matemática - Secundaria",
    "Profesor/a de Lengua y Literatura - Secundaria",
    "Profesor/a de Inglés - Secundaria",
    "Profesor/a de Biología",
    "Profesor/a de Historia",
    "Profesor/a de Geografía",
    "Preceptor/a",
    "Bibliotecario/a Escolar",
    "Coordinador/a Pedagógico/a",
    "Auxiliar Docente",
]


class ArgentinaGenerator(CountryGenerator):
    """Argentina-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Argentina"
    
    def get_country_code(self) -> str:
        return "argentina"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_ARGENTINA_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return ARGENTINA_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return ARGENTINA_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return ARGENTINA_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["payslip", "employment_certificate", "signed_school_letter"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Argentina document"""
        if doc_type == "payslip":
            return self._generate_payslip(first, last, school, position)
        elif doc_type == "employment_certificate":
            return self._generate_employment_certificate(first, last, school, position, dob)
        elif doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_payslip(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Payment Slip (Recibo de Sueldo)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 56)
        font_header = load_font('arialbd', 42)
        font_normal = load_font('arial', 36)
        font_bold = load_font('arialbd', 36)
        font_small = load_font('arial', 30)
        
        # Argentine flag colors header
        draw.rectangle([(0, 0), (w, 50)], fill=(116, 172, 223))
        draw.rectangle([(0, 50), (w, 100)], fill=(255, 255, 255))
        draw.rectangle([(0, 100), (w, 150)], fill=(116, 172, 223))
        
        # Title
        y = 220
        draw.text((w//2, y), "RECIBO DE SUELDO", fill=(116, 172, 223), font=font_title, anchor="mm")
        
        # School info box
        y = 320
        draw.rectangle([(150, y), (w-150, y+280)], fill=(250, 250, 255), outline=(116, 172, 223), width=4)
        
        y += 40
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} ({school['postcode']})", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"Tel: {school['phone']}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Period info
        y += 120
        current_month = datetime.now().strftime("%B %Y")
        recibo_number = f"RS-{random.randint(10000, 99999)}"
        
        info_items = [
            ("Número de Recibo:", recibo_number),
            ("Período:", current_month),
            ("", ""),
        ]
        
        for label, value in info_items:
            if label:
                draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
                draw.text((700, y), value, fill=(0, 0, 0), font=font_normal)
                y += 60
            else:
                y += 30
        
        # Employee data
        y += 20
        draw.rectangle([(150, y), (w-150, y+60)], fill=(116, 172, 223))
        draw.text((w//2, y+30), "DATOS DEL EMPLEADO", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        cuil = f"20-{random.randint(10000000, 99999999)}-{random.randint(0, 9)}"
        
        employee_data = [
            ("Nombre y Apellido", f"{first} {last}"),
            ("CUIL", cuil),
            ("Cargo", position),
            ("Categoría", f"Categoría {random.randint(1, 5)}"),
        ]
        
        for label, value in employee_data:
            draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
            draw.text((700, y), value, fill=(0, 0, 0), font=font_normal)
            y += 60
        
        # Salary details
        y += 60
        draw.rectangle([(150, y), (w-150, y+60)], fill=(116, 172, 223))
        draw.text((w//2, y+30), "HABERES", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        base_salary = random.randint(150000, 350000)
        
        # Income section
        income_items = [
            ("Sueldo Básico", f"$ {base_salary:,}"),
            ("Antigüedad", f"$ {int(base_salary * 0.15):,}"),
            ("Presentismo", f"$ {int(base_salary * 0.10):,}"),
        ]
        
        for label, value in income_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        total_gross = int(base_salary * 1.25)
        
        # Total
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(116, 172, 223), width=4)
        y += 50
        draw.text((250, y), "TOTAL HABERES", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"$ {total_gross:,}", fill=(116, 172, 223), font=font_bold, anchor="ra")
        
        # Deductions
        y += 100
        draw.rectangle([(150, y), (w-150, y+60)], fill=(100, 100, 100))
        draw.text((w//2, y+30), "DESCUENTOS", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        deduction_items = [
            ("Jubilación (11%)", f"$ {int(total_gross * 0.11):,}"),
            ("Obra Social (3%)", f"$ {int(total_gross * 0.03):,}"),
            ("Ley 19032 (3%)", f"$ {int(total_gross * 0.03):,}"),
        ]
        
        for label, value in deduction_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        total_deduction = int(total_gross * 0.17)
        net_salary = total_gross - total_deduction
        
        # Net salary
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(100, 100, 100), width=4)
        y += 50
        draw.text((250, y), "NETO A COBRAR", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"$ {net_salary:,}", fill=(0, 128, 0), font=font_bold, anchor="ra")
        
        # Signature
        y = h - 550
        draw.text((w//2, y), f"{school['city']}, {datetime.now().strftime('%d de %B de %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w-600, y), "Administración", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 150
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=2)
        y += 40
        draw.text((w-600, y), "Firma Autorizada", fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 150
        draw.line([(150, y), (w-150, y)], fill=(116, 172, 223), width=3)
        y += 40
        draw.text((w//2, y), "Documento emitido electrónicamente - Válido sin firma", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_employment_certificate(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Employment Certificate (Certificado de Trabajo)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 52)
        font_header = load_font('arialbd', 44)
        font_normal = load_font('arial', 38)
        font_bold = load_font('arialbd', 38)
        font_small = load_font('arial', 32)
        
        # Header with Argentine colors
        draw.rectangle([(0, 0), (w, 50)], fill=(116, 172, 223))
        draw.rectangle([(0, 50), (w, 100)], fill=(255, 255, 255))
        draw.rectangle([(0, 100), (w, 150)], fill=(116, 172, 223))
        
        # School header
        y = 220
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Tel: {school['phone']}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 60
        draw.rectangle([(200, y), (w-200, y+6)], fill=(116, 172, 223))
        
        # Document title
        y += 100
        draw.rectangle([(150, y), (w-150, y+100)], fill=(250, 250, 255))
        draw.text((w//2, y+50), "CERTIFICADO DE TRABAJO", fill=(116, 172, 223), font=font_header, anchor="mm")
        
        # Reference number
        y += 150
        ref_number = f"Nº {random.randint(1000, 9999)}/{datetime.now().year}"
        draw.text((w//2, y), ref_number, fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Content
        y += 120
        content_lines = [
            "El que suscribe, en su carácter de Rector/a del",
            f"{school['name']}, certifica que:",
        ]
        
        for line in content_lines:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55
        
        y += 50
        cuil = f"20-{random.randint(10000000, 99999999)}-{random.randint(0, 9)}"
        dni = f"{random.randint(10000000, 45000000)}"
        
        teacher_data = [
            ("Nombre y Apellido", f": {first} {last}"),
            ("DNI", f": {dni}"),
            ("CUIL", f": {cuil}"),
            ("Fecha de Nacimiento", f": {dob}"),
            ("Cargo", f": {position}"),
            ("Antigüedad", f": {random.randint(3, 15)} años"),
        ]
        
        for label, value in teacher_data:
            draw.text((500, y), label, fill=(0, 0, 0), font=font_bold)
            draw.text((1000, y), value, fill=(0, 0, 0), font=font_normal)
            y += 65
        
        y += 80
        cert_text = [
            f"Se desempeña como {position} en esta institución",
            f"desde el año {datetime.now().year - random.randint(3, 15)}, cumpliendo con todas",
            "las obligaciones inherentes al cargo y manteniendo una conducta",
            "intachable durante todo el período.",
            "",
            "Se extiende el presente certificado a pedido del interesado/a",
            "para ser presentado ante las autoridades que lo requieran.",
        ]
        
        for line in cert_text:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55 if line else 30
        
        # Signature
        y += 100
        draw.text((w//2, y), f"{school['city']}, {datetime.now().strftime('%d de %B de %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 80
        draw.text((w-600, y), "Rectorado", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Stamp placeholder
        stamp_x = w - 600
        stamp_y = y + 120
        draw.ellipse([(stamp_x-90, stamp_y-90), (stamp_x+90, stamp_y+90)], outline=(116, 172, 223), width=8)
        draw.text((stamp_x, stamp_y), "SELLO", fill=(116, 172, 223), font=font_header, anchor="mm")
        
        y += 200
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=3)
        y += 45
        draw.text((w-600, y), "Rector/a", fill=(0, 0, 0), font=font_small, anchor="mm")
        y += 40
        draw.text((w-600, y), school['name'], fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(116, 172, 223), width=3)
        y += 45
        draw.text((w//2, y), f"Documento oficial de {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter (Carta Institucional)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 52)
        font_header = load_font('arialbd', 44)
        font_normal = load_font('arial', 38)
        font_bold = load_font('arialbd', 38)
        font_small = load_font('arial', 32)
        
        # Argentine flag header
        draw.rectangle([(0, 0), (w, 60)], fill=(116, 172, 223))
        draw.rectangle([(0, 60), (w, 100)], fill=(255, 255, 255))
        draw.rectangle([(0, 100), (w, 160)], fill=(116, 172, 223))
        
        # School header
        y = 230
        draw.text((w//2, y), school["name"].upper(), fill=(116, 172, 223), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} - {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Tel: {school['phone']} | Web: {school['domain']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+6)], fill=(116, 172, 223))
        
        # Title
        y += 100
        draw.text((w//2, y), "CARTA DE PRESENTACIÓN INSTITUCIONAL", fill=(116, 172, 223), 
                 font=font_header, anchor="mm")
        
        # Date
        y += 100
        draw.text((w-300, y), datetime.now().strftime("%d de %B de %Y"), 
                 fill=(80, 80, 80), font=font_normal, anchor="rm")
        
        # Salutation
        y += 100
        draw.text((250, y), "A QUIEN CORRESPONDA:", fill=(40, 40, 40), font=font_bold)
        
        # Body
        y += 100
        content_lines = [
            f"Tengo el agrado de dirigirme a Ud./Uds. con el objeto de presentar",
            f"al/la Profesor/a {first} {last}, quien se desempeña en este",
            f"establecimiento educativo como {position}.",
            "",
            f"El/La Profesor/a {last} forma parte del plantel docente de nuestra",
            f"institución desde el año {datetime.now().year - random.randint(3, 10)}, demostrando",
            "durante todo este tiempo un alto nivel de profesionalismo, dedicación",
            "y compromiso con la tarea educativa.",
            "",
            "Entre sus responsabilidades se encuentran:",
            "• Planificación y dictado de clases",
            "• Evaluación del proceso de aprendizaje",
            "• Tutoría y orientación pedagógica",
            "• Participación en proyectos institucionales",
            "",
            f"El/La Profesor/a {last} cumple con todos los requisitos establecidos",
            "por la normativa vigente y mantiene actualizada su formación docente.",
            "",
            "Sin otro particular, saludo a Ud./Uds. muy atentamente.",
        ]
        
        for line in content_lines:
            if line.startswith("•"):
                draw.text((350, y), line, fill=(60, 60, 60), font=font_normal)
                y += 55
            elif line:
                draw.text((250, y), line, fill=(60, 60, 60), font=font_normal)
                y += 55
            else:
                y += 30
        
        # Signature section
        y += 80
        
        y += 120
        draw.line([(250, y), (850, y)], fill=(116, 172, 223), width=3)
        y += 45
        draw.text((250, y), "Rector/a", fill=(0, 0, 0), font=font_bold)
        y += 50
        draw.text((250, y), school['name'], fill=(80, 80, 80), font=font_small)
        
        # School stamp
        stamp_x, stamp_y = 1800, y - 120
        draw.ellipse([(stamp_x-80, stamp_y-80), (stamp_x+80, stamp_y+80)], 
                    outline=(116, 172, 223), width=8)
        draw.text((stamp_x, stamp_y), "SELLO", fill=(116, 172, 223), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(116, 172, 223), width=3)
        y += 45
        draw.text((w//2, y), f"Documento oficial del {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
