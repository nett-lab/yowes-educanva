"""
Mexico data and document generators

Mexican teacher verification requirements:
1. Teaching ID (Credencial de Profesor)
2. Signed School Letter (Carta de la Escuela)
3. Employment Certificate (Constancia Laboral)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Mexico Universities Database
DEFAULT_MEXICO_SCHOOLS = [
    {"name": "Colegio Americano de Puebla", "address": "Boulevard Atlixcáyotl 5503", "city": "Puebla", "region": "Puebla", "postcode": "72830", "phone": "+52 222 303 0500", "domain": "cap.edu.mx"},
    {"name": "Colegio Cumbres Lomas", "address": "Av. de las Fuentes 480", "city": "Ciudad de México", "region": "CDMX", "postcode": "05120", "phone": "+52 55 5246 4600", "domain": "cumbres.edu.mx"},
    {"name": "Instituto Cumbres Bosques", "address": "Bosques de Pirules 17", "city": "Huixquilucan", "region": "Estado de México", "postcode": "52787", "phone": "+52 55 5251 0500", "domain": "cumbresbosques.edu.mx"},
    {"name": "Colegio Greengates", "address": "Av. Circunvalación Pte. 102", "city": "Ciudad López Mateos", "region": "Estado de México", "postcode": "52950", "phone": "+52 55 5373 0088", "domain": "greengates.edu.mx"},
    {"name": "American School Foundation", "address": "Bondojito 215", "city": "Ciudad de México", "region": "CDMX", "postcode": "01120", "phone": "+52 55 5227 4900", "domain": "asf.edu.mx"},
    {"name": "Colegio Eton", "address": "Calzada de las Águilas 1500", "city": "Ciudad de México", "region": "CDMX", "postcode": "01710", "phone": "+52 55 5635 6210", "domain": "eton.edu.mx"},
    {"name": "Liceo Mexicano Japonés", "address": "Av. Pirules 23", "city": "Ciudad de México", "region": "CDMX", "postcode": "01900", "phone": "+52 55 5683 6033", "domain": "liceomx.edu.mx"},
    {"name": "Colegio Williams", "address": "Calle Sur 136 No. 39", "city": "Ciudad de México", "region": "CDMX", "postcode": "01120", "phone": "+52 55 5273 7000", "domain": "colegiowilliams.edu.mx"},
    {"name": "Instituto Tomás Alva Edison", "address": "Bosques de Moctezuma 50", "city": "Naucalpan", "region": "Estado de México", "postcode": "53220", "phone": "+52 55 5294 1500", "domain": "edison.edu.mx"},
    {"name": "Colegio Franco Mexicano", "address": "Homero 1521", "city": "Ciudad de México", "region": "CDMX", "postcode": "11560", "phone": "+52 55 5557 8166", "domain": "francomex.edu.mx"},
    {"name": "Colegio Alemán Alexander von Humboldt", "address": "Bosque de los Cedros 525", "city": "Ciudad de México", "region": "CDMX", "postcode": "05120", "phone": "+52 55 5251 0309", "domain": "humboldt.edu.mx"},
    {"name": "Instituto Cumbres Guadalajara", "address": "Av. Patria 1201", "city": "Zapopan", "region": "Jalisco", "postcode": "45110", "phone": "+52 33 3683 0050", "domain": "cumbresgdl.edu.mx"},
    {"name": "Colegio Internacional de México", "address": "Camino al Olivo 35", "city": "Ciudad de México", "region": "CDMX", "postcode": "10200", "phone": "+52 55 5681 6600", "domain": "cim.edu.mx"},
    {"name": "Colegio Lestonnac", "address": "Av. Universidad 1330", "city": "Coyoacán", "region": "CDMX", "postcode": "04360", "phone": "+52 55 5658 4055", "domain": "lestonnac.edu.mx"},
    {"name": "Instituto Anglo Mexicano de Cultura", "address": "Av. José María Morelos 332", "city": "Cuernavaca", "region": "Morelos", "postcode": "62240", "phone": "+52 777 313 8530", "domain": "anglo.edu.mx"},
]

# Mexican Names
MEXICO_FIRST_NAMES = [
    "José", "María", "Juan", "Guadalupe", "Francisco", "Juana", "Antonio", "Jesús",
    "Miguel", "Pedro", "Alejandro", "Manuel", "Margarita", "Rosa", "Francisco", "Ana",
    "Carlos", "Martha", "Luis", "Patricia", "Jorge", "Verónica", "Roberto", "Gabriela",
    "Fernando", "Claudia", "Eduardo", "Carmen", "Daniel", "Laura", "Ricardo", "Diana"
]

MEXICO_LAST_NAMES = [
    "García", "Martínez", "López", "Hernández", "González", "Pérez", "Sánchez", "Ramírez",
    "Torres", "Flores", "Rivera", "Gómez", "Díaz", "Cruz", "Morales", "Reyes",
    "Gutiérrez", "Jiménez", "Ruiz", "Mendoza", "Vázquez", "Álvarez", "Castillo", "Romero",
    "Herrera", "Medina", "Aguilar", "Ortiz", "Vargas", "Chávez", "Ramos", "Fernández"
]

# Mexican K-12 Teaching Positions (Preescolar, Primaria, Secundaria, Preparatoria)
MEXICO_TEACHING_POSITIONS = [
    "Educadora de Preescolar",
    "Maestro/a de Preescolar",
    "Maestro/a de Primaria",
    "Maestro/a de Grupo - Primaria",
    "Maestro/a de Inglés - Primaria",
    "Maestro/a de Educación Física - Primaria",
    "Maestro/a de Computación",
    "Profesor/a de Matemáticas - Secundaria",
    "Profesor/a de Español - Secundaria",
    "Profesor/a de Inglés - Secundaria",
    "Profesor/a de Ciencias - Biología",
    "Profesor/a de Historia de México",
    "Profesor/a de Geografía",
    "Profesor/a de Formación Cívica y Ética",
    "Profesor/a de Preparatoria",
    "Tutor/a de Grupo",
    "Orientador/a Educativo/a",
    "Coordinador/a Académico/a",
    "Subdirector/a Académico/a",
]


class MexicoGenerator(CountryGenerator):
    """Mexico-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Mexico"
    
    def get_country_code(self) -> str:
        return "mexico"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_MEXICO_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return MEXICO_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return MEXICO_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return MEXICO_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["teaching_id", "signed_school_letter", "employment_certificate"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Mexico document"""
        if doc_type == "teaching_id":
            return self._generate_teaching_id(first, last, school, position, dob)
        elif doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        elif doc_type == "employment_certificate":
            return self._generate_employment_certificate(first, last, school, position, dob)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_teaching_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Mexican Teaching ID Card"""
        # Create image 1000x630 pixels
        img = Image.new('RGB', (1000, 630), color='white')
        draw = ImageDraw.Draw(img)
        
        # Colors
        header_color = (139, 0, 0)  # Dark red (Mexican flag color)
        text_color = (0, 0, 0)
        
        # Draw header
        draw.rectangle([0, 0, 1000, 120], fill=header_color)
        
        # Title
        title_font = load_font(48, bold=True)
        draw.text((500, 60), "CREDENCIAL DE PROFESOR", font=title_font, fill='white', anchor='mm')
        
        # Photo placeholder
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(person_id=person_id, gender=gender)
        if photo:
            photo = photo.resize((200, 240))
            img.paste(photo, (50, 160))
        else:
            draw.rectangle([50, 160, 250, 400], fill=(200, 200, 200))
            avatar = generate_initials_avatar(first, last, size=200)
            img.paste(avatar, (50, 160))
        
        # Information
        info_font = load_font(24, bold=True)
        value_font = load_font(22)
        
        y_pos = 170
        spacing = 50
        
        # Name
        draw.text((280, y_pos), "NOMBRE:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), f"{first} {last}", font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Position
        draw.text((280, y_pos), "POSICIÓN:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), position, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # School
        draw.text((280, y_pos), "INSTITUCIÓN:", font=info_font, fill=text_color)
        # Wrap long school names
        school_name = school['name']
        if len(school_name) > 35:
            words = school_name.split()
            line1 = ""
            line2 = ""
            for word in words:
                if len(line1) + len(word) < 35:
                    line1 += word + " "
                else:
                    line2 += word + " "
            draw.text((280, y_pos + 25), line1.strip(), font=value_font, fill=text_color)
            draw.text((280, y_pos + 45), line2.strip(), font=value_font, fill=text_color)
        else:
            draw.text((280, y_pos + 25), school_name, font=value_font, fill=text_color)
        
        y_pos += spacing + 30
        
        # ID Number
        id_number = f"MX{random.randint(100000, 999999)}"
        draw.text((280, y_pos), "No. CREDENCIAL:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), id_number, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Issue date
        issue_date = datetime.now().strftime("%d/%m/%Y")
        draw.text((280, y_pos), "FECHA DE EMISIÓN:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), issue_date, font=value_font, fill=text_color)
        
        # Footer
        footer_font = load_font(16)
        draw.text((500, 600), "SEP - Secretaría de Educación Pública", font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter"""
        # Create image 1000x1400 pixels (letter size)
        img = Image.new('RGB', (1000, 1400), color='white')
        draw = ImageDraw.Draw(img)
        
        text_color = (0, 0, 0)
        
        # School letterhead
        header_font = load_font(32, bold=True)
        draw.text((500, 80), school['name'].upper(), font=header_font, fill=text_color, anchor='mm')
        
        address_font = load_font(18)
        draw.text((500, 120), f"{school['address']}, {school['city']}, {school['region']}", 
                 font=address_font, fill=text_color, anchor='mm')
        draw.text((500, 145), f"C.P. {school['postcode']} | Tel: {school['phone']}", 
                 font=address_font, fill=text_color, anchor='mm')
        
        # Draw line
        draw.line([100, 180, 900, 180], fill=text_color, width=2)
        
        # Date
        date_font = load_font(20)
        current_date = datetime.now().strftime("%d de %B de %Y")
        month_translation = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        for eng, esp in month_translation.items():
            current_date = current_date.replace(eng, esp)
        
        draw.text((800, 230), current_date, font=date_font, fill=text_color, anchor='rm')
        
        # Letter title
        title_font = load_font(24, bold=True)
        draw.text((500, 300), "CARTA DE CONSTANCIA LABORAL", font=title_font, fill=text_color, anchor='mm')
        
        # Letter body
        body_font = load_font(20)
        y_pos = 370
        line_spacing = 35
        
        lines = [
            "A QUIEN CORRESPONDA:",
            "",
            f"Por medio de la presente, se hace constar que el/la {position.lower()}",
            f"{first} {last}, labora en esta institución educativa desde",
            f"el año {datetime.now().year - random.randint(1, 5)}.",
            "",
            "Durante su desempeño profesional, ha demostrado responsabilidad,",
            "compromiso y dedicación en sus funciones académicas, contribuyendo",
            "significativamente al desarrollo educativo de nuestros estudiantes.",
            "",
            "Se extiende la presente a solicitud del interesado para los fines",
            "que estime conveniente.",
            "",
            "ATENTAMENTE,",
        ]
        
        for line in lines:
            draw.text((100, y_pos), line, font=body_font, fill=text_color)
            y_pos += line_spacing
        
        # Signature area
        y_pos += 80
        draw.line([350, y_pos, 650, y_pos], fill=text_color, width=2)
        
        sig_font = load_font(18, bold=True)
        draw.text((500, y_pos + 20), "Director/a Académico/a", font=sig_font, fill=text_color, anchor='mm')
        draw.text((500, y_pos + 45), school['name'], font=address_font, fill=text_color, anchor='mm')
        
        # Seal placeholder
        draw.ellipse([400, y_pos - 120, 600, y_pos - 20], outline=text_color, width=3)
        seal_font = load_font(16)
        draw.text((500, y_pos - 70), "SELLO", font=seal_font, fill=text_color, anchor='mm')
        draw.text((500, y_pos - 50), "OFICIAL", font=seal_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_employment_certificate(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Employment Certificate (Constancia Laboral)"""
        # Create image 1000x1400 pixels
        img = Image.new('RGB', (1000, 1400), color='white')
        draw = ImageDraw.Draw(img)
        
        text_color = (0, 0, 0)
        header_color = (139, 0, 0)
        
        # Header with color
        draw.rectangle([0, 0, 1000, 150], fill=header_color)
        
        header_font = load_font(36, bold=True)
        draw.text((500, 75), "CONSTANCIA LABORAL", font=header_font, fill='white', anchor='mm')
        
        # School info
        school_font = load_font(24, bold=True)
        info_font = load_font(18)
        
        draw.text((500, 220), school['name'], font=school_font, fill=text_color, anchor='mm')
        draw.text((500, 255), f"{school['address']}, {school['city']}", font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 285), f"{school['region']}, México - C.P. {school['postcode']}", 
                 font=info_font, fill=text_color, anchor='mm')
        
        # Document number
        doc_number = f"CONST-{random.randint(1000, 9999)}-{datetime.now().year}"
        draw.text((500, 330), f"No. de Documento: {doc_number}", font=info_font, fill=text_color, anchor='mm')
        
        # Draw separator
        draw.line([100, 360, 900, 360], fill=text_color, width=2)
        
        # Certificate content
        body_font = load_font(20)
        y_pos = 410
        spacing = 40
        
        content = [
            "La Dirección de Recursos Humanos hace constar que:",
            "",
            f"Nombre: {first} {last}",
            f"Fecha de Nacimiento: {dob}",
            f"Posición: {position}",
            "",
            f"Labora activamente en esta institución desde el {datetime.now().day}",
            f"de {datetime.now().strftime('%B')} de {datetime.now().year - random.randint(1, 5)}, desempeñando",
            "las siguientes funciones:",
            "",
            "• Planificación y ejecución de actividades académicas",
            "• Evaluación del desempeño estudiantil",
            "• Participación en juntas académicas y consejos técnicos",
            "• Actualización continua en métodos pedagógicos",
            "",
            "El/La profesor/a cuenta con contrato vigente de tiempo completo",
            "y se encuentra al corriente de todas sus obligaciones laborales.",
            "",
            "Se extiende la presente constancia para los fines que al",
            "interesado convengan.",
        ]
        
        for line in content:
            if line.startswith("•"):
                draw.text((120, y_pos), line, font=body_font, fill=text_color)
            else:
                draw.text((100, y_pos), line, font=body_font, fill=text_color)
            y_pos += spacing
        
        # Date and signatures
        y_pos += 40
        current_date = datetime.now().strftime("%d/%m/%Y")
        date_font = load_font(18)
        draw.text((500, y_pos), f"Ciudad de México, {current_date}", font=date_font, fill=text_color, anchor='mm')
        
        # Signature lines
        y_pos += 80
        draw.line([150, y_pos, 450, y_pos], fill=text_color, width=2)
        draw.line([550, y_pos, 850, y_pos], fill=text_color, width=2)
        
        sig_font = load_font(16, bold=True)
        draw.text((300, y_pos + 20), "Director de RRHH", font=sig_font, fill=text_color, anchor='mm')
        draw.text((700, y_pos + 20), "Director General", font=sig_font, fill=text_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 1350), "Documento válido con firmas y sello oficial", 
                 font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


# Create generator instance
generator = MexicoGenerator()
