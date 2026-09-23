"""
Spain data and document generators

Spanish teacher verification requirements:
1. Teaching ID (Carné de Profesor)
2. Signed School Letter
3. Employment Contract (Contrato Laboral)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Spain K-12 Schools Database (Infantil, Primaria, ESO, Bachillerato)
DEFAULT_SPAIN_SCHOOLS = [
    {"name": "Colegio Sagrado Corazón", "address": "Calle Rosario 14", "city": "Madrid", "region": "Comunidad de Madrid", "postcode": "28005", "phone": "+34 91 365 12 80", "domain": "sagradocorazon.edu.es"},
    {"name": "Colegio Montserrat", "address": "Carrer de Copèrnic 84", "city": "Barcelona", "region": "Cataluña", "postcode": "08006", "phone": "+34 93 209 56 33", "domain": "cmontserrat.org"},
    {"name": "Colegio San José", "address": "Calle de la Reina 3", "city": "Valencia", "region": "Comunidad Valenciana", "postcode": "46011", "phone": "+34 96 371 92 40", "domain": "colegiosanjose.es"},
    {"name": "Colegio Santa María del Pilar", "address": "Calle Reyes Magos 3", "city": "Madrid", "region": "Comunidad de Madrid", "postcode": "28009", "phone": "+34 91 574 70 50", "domain": "smpilar.es"},
    {"name": "Colegio Inmaculada Jesuitas", "address": "Avenida de la Soledad 15", "city": "Alicante", "region": "Comunidad Valenciana", "postcode": "03005", "phone": "+34 96 521 61 10", "domain": "inmaculadajesuitas.es"},
    {"name": "Colegio Virgen de Europa", "address": "Calle Valle de Santa Ana 1", "city": "Boadilla del Monte", "region": "Comunidad de Madrid", "postcode": "28660", "phone": "+34 91 633 01 55", "domain": "colegiovirgendeeuropa.es"},
    {"name": "Colegio Aldovea", "address": "Camino Ancho 87", "city": "Alcobendas", "region": "Comunidad de Madrid", "postcode": "28109", "phone": "+34 91 650 19 00", "domain": "colegioaldovea.com"},
    {"name": "Colegio Mirasur", "address": "Avenida del Mediterráneo 56", "city": "Pinto", "region": "Comunidad de Madrid", "postcode": "28320", "phone": "+34 91 691 79 50", "domain": "colegiomirasur.com"},
    {"name": "Colegio Ágora Lledó International", "address": "Camino Caminás", "city": "Castellón de la Plana", "region": "Comunidad Valenciana", "postcode": "12006", "phone": "+34 964 25 18 90", "domain": "lledo.agorainternational.es"},
    {"name": "Colegio Highlands El Encinar", "address": "Camino Sur de la Moraleja 22", "city": "Alcobendas", "region": "Comunidad de Madrid", "postcode": "28109", "phone": "+34 91 650 02 02", "domain": "highlandsschool.es"},
    {"name": "Colegio Liceo Sorolla", "address": "Calle Camino Ancho 21", "city": "Pozuelo de Alarcón", "region": "Comunidad de Madrid", "postcode": "28223", "phone": "+34 91 352 01 00", "domain": "liceosorolla.es"},
    {"name": "Colegio Arenas Internacional", "address": "Avenida del Atlántico 27", "city": "Las Palmas de Gran Canaria", "region": "Canarias", "postcode": "35100", "phone": "+34 928 76 80 00", "domain": "colegioarenas.es"},
    {"name": "Colegio Patrocinio de San José", "address": "Calle Hernani 32", "city": "Madrid", "region": "Comunidad de Madrid", "postcode": "28020", "phone": "+34 91 553 47 84", "domain": "patrociniosanjose.es"},
    {"name": "Colegio Sant Ignasi", "address": "Carrer de Sarrià 95", "city": "Barcelona", "region": "Cataluña", "postcode": "08017", "phone": "+34 93 602 30 00", "domain": "santignasi.fje.edu"},
    {"name": "Colegio Juan de Lanuza", "address": "Camino del Vado 2", "city": "Zaragoza", "region": "Aragón", "postcode": "50015", "phone": "+34 976 51 78 49", "domain": "juandelanuza.org"},
]

# Spanish Names
SPAIN_FIRST_NAMES = [
    "Antonio", "María", "José", "Carmen", "Francisco", "Ana", "Manuel", "Isabel",
    "David", "Dolores", "Daniel", "Pilar", "Carlos", "Teresa", "Miguel", "Rosa",
    "Javier", "Josefa", "Pedro", "Cristina", "Alejandro", "Francisca", "Rafael", "Laura",
    "Pablo", "Elena", "Sergio", "Lucía", "Jorge", "Mercedes", "Alberto", "Marta"
]

SPAIN_LAST_NAMES = [
    "García", "Rodríguez", "González", "Fernández", "López", "Martínez", "Sánchez", "Pérez",
    "Gómez", "Martín", "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno", "Álvarez",
    "Muñoz", "Romero", "Alonso", "Gutiérrez", "Navarro", "Torres", "Domínguez", "Vázquez",
    "Ramos", "Gil", "Ramírez", "Serrano", "Blanco", "Suárez", "Molina", "Morales"
]

# Spanish K-12 Teaching Positions (Infantil, Primaria, ESO, Bachillerato)
SPAIN_TEACHING_POSITIONS = [
    "Maestro/a de Educación Infantil",
    "Maestro/a de Educación Primaria",
    "Maestro/a de Inglés - Primaria",
    "Maestro/a de Educación Física - Primaria",
    "Maestro/a de Música - Primaria",
    "Maestro/a de Pedagogía Terapéutica",
    "Maestro/a de Audición y Lenguaje",
    "Profesor/a de Matemáticas - Secundaria",
    "Profesor/a de Lengua Castellana y Literatura",
    "Profesor/a de Inglés - Secundaria",
    "Profesor/a de Biología y Geología",
    "Profesor/a de Física y Química",
    "Profesor/a de Geografía e Historia",
    "Profesor/a de Educación Física - Secundaria",
    "Profesor/a de Tecnología",
    "Tutor/a de Curso",
    "Orientador/a Escolar",
    "Coordinador/a de Etapa",
    "Jefe/a de Estudios",
]


class SpainGenerator(CountryGenerator):
    """Spain-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Spain"
    
    def get_country_code(self) -> str:
        return "spain"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_SPAIN_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return SPAIN_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return SPAIN_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return SPAIN_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["teaching_id", "signed_school_letter", "employment_contract"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Spain document"""
        if doc_type == "teaching_id":
            return self._generate_teaching_id(first, last, school, position, dob)
        elif doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        elif doc_type == "employment_contract":
            return self._generate_employment_contract(first, last, school, position, dob)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_teaching_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Teaching ID Card (Carné de Profesor)"""
        w, h = 1280, 800
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 42)
            font_header = load_font("arialbd", 32)
            font_normal = load_font("arial", 26)
            font_bold = load_font("arialbd", 28)
            font_small = load_font("arial", 22)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Spanish flag colors background
        stripe_height = h // 4
        draw.rectangle([(0, 0), (w, stripe_height)], fill=(200, 16, 46))
        draw.rectangle([(0, stripe_height), (w, 3*stripe_height)], fill=(251, 192, 45))
        draw.rectangle([(0, 3*stripe_height), (w, h)], fill=(200, 16, 46))
        
        # White card area
        card_margin = 35
        draw.rectangle([(card_margin, card_margin), (w-card_margin, h-card_margin)], 
                      fill=(255, 255, 255), outline=(200, 16, 46), width=6)
        
        # Header
        y = 65
        draw.text((w//2, y), "CARNÉ DE PROFESOR", fill=(200, 16, 46), 
                 font=font_title, anchor="mm")
        y += 45
        draw.text((w//2, y), school["name"].upper(), fill=(80, 80, 80), 
                 font=font_header, anchor="mm")
        
        y += 40
        draw.line([(80, y), (w-80, y)], fill=(251, 192, 45), width=4)
        
        # Photo section
        photo_size = (200, 250)
        photo_x, photo_y = 90, 220
        
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(200, 16, 46))
        
        draw.rectangle([(photo_x-4, photo_y-4), (photo_x+photo_size[0]+4, photo_y+photo_size[1]+4)], 
                      outline=(200, 16, 46), width=3)
        img.paste(photo, (photo_x, photo_y))
        
        # Information section
        info_x = 330
        y = 230
        
        dni = f"{random.randint(10000000, 99999999)}{random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])}"
        
        info_items = [
            ("NOMBRE:", f"{first} {last}".upper()),
            ("DNI:", dni),
            ("POSICIÓN:", position),
            ("CENTRO:", school['city']),
            ("FECHA NAC.:", dob),
            ("VÁLIDO HASTA:", f"{datetime.now().month:02d}/{datetime.now().year + 4}"),
        ]
        
        for label, value in info_items:
            draw.text((info_x, y), label, fill=(100, 100, 100), font=font_small)
            y += 30
            draw.text((info_x, y), value, fill=(0, 0, 0), font=font_bold)
            y += 50
        
        # ID number at bottom
        y = h - 100
        id_num = f"ESP-{random.randint(100000, 999999)}"
        draw.text((w//2, y), f"Nº: {id_num}", fill=(200, 16, 46), font=font_bold, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter (Carta del Centro)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 44)
            font_normal = load_font("arial", 38)
            font_bold = load_font("arialbd", 38)
            font_small = load_font("arial", 32)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Spanish flag header
        draw.rectangle([(0, 0), (w, 40)], fill=(200, 16, 46))
        draw.rectangle([(0, 40), (w, 100)], fill=(251, 192, 45))
        draw.rectangle([(0, 100), (w, 140)], fill=(200, 16, 46))
        
        # School header
        y = 210
        draw.text((w//2, y), school["name"].upper(), fill=(200, 16, 46), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['city']} ({school['region']})", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Tel: {school['phone']} | Web: {school['domain']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+6)], fill=(200, 16, 46))
        
        # Title
        y += 100
        draw.text((w//2, y), "CERTIFICADO DE EMPLEO", fill=(200, 16, 46), 
                 font=font_header, anchor="mm")
        
        # Date
        y += 100
        months_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        date_str = f"{datetime.now().day} de {months_es[datetime.now().month-1]} de {datetime.now().year}"
        draw.text((w-300, y), date_str, fill=(80, 80, 80), font=font_normal, anchor="rm")
        
        # Salutation
        y += 100
        draw.text((250, y), "A QUIEN CORRESPONDA,", fill=(40, 40, 40), font=font_bold)
        
        # Body
        y += 100
        content_lines = [
            f"Por medio de la presente, certifico que D./Dña. {first} {last}",
            f"trabaja en el {school['name']} como {position}",
            "desde el curso académico " + f"{datetime.now().year - random.randint(2, 8)}-{datetime.now().year - random.randint(2, 8) + 1}.",
            "",
            "Sus responsabilidades profesionales incluyen:",
            "• Impartir clases según el currículo establecido",
            "• Evaluación y seguimiento del progreso del alumnado",
            "• Tutoría y orientación académica",
            "• Participación en actividades del centro",
            "",
            f"D./Dña. {first} {last} cumple con todos los requisitos",
            "establecidos por la legislación educativa vigente y mantiene",
            "su titulación profesional en vigor.",
            "",
            "Se expide el presente certificado a petición del interesado/a",
            "para los fines que estime convenientes.",
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
        draw.text((250, y), "Atentamente,", fill=(40, 40, 40), font=font_normal)
        
        y += 120
        draw.line([(250, y), (850, y)], fill=(200, 16, 46), width=3)
        y += 45
        draw.text((250, y), "El/La Director/a", fill=(0, 0, 0), font=font_bold)
        y += 50
        draw.text((250, y), school['name'], fill=(80, 80, 80), font=font_small)
        
        # School stamp
        stamp_x, stamp_y = 1800, y - 120
        draw.ellipse([(stamp_x-80, stamp_y-80), (stamp_x+80, stamp_y+80)], 
                    outline=(200, 16, 46), width=8)
        draw.text((stamp_x, stamp_y), "SELLO", fill=(200, 16, 46), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(200, 16, 46), width=3)
        y += 45
        draw.text((w//2, y), f"Documento oficial del {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_employment_contract(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Employment Contract (Contrato Laboral)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 54)
            font_header = load_font("arialbd", 42)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Header with Spanish colors
        draw.rectangle([(0, 0), (w, 50)], fill=(200, 16, 46))
        draw.rectangle([(0, 50), (w, 100)], fill=(251, 192, 45))
        draw.rectangle([(0, 100), (w, 150)], fill=(200, 16, 46))
        
        # Title
        y = 220
        draw.text((w//2, y), "CONTRATO LABORAL", fill=(200, 16, 46), 
                 font=font_title, anchor="mm")
        y += 70
        draw.text((w//2, y), "Contrato de Trabajo del Personal Docente", 
                 fill=(100, 100, 100), font=font_header, anchor="mm")
        
        # Contract content
        y += 120
        dni = f"{random.randint(10000000, 99999999)}{random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])}"
        contract_num = f"CT-{random.randint(1000, 9999)}/{datetime.now().year}"
        
        content = [
            f"Número de Contrato: {contract_num}",
            "",
            "PRIMERA: PARTES CONTRATANTES",
            "",
            f"De una parte, {school['name']}, con domicilio en",
            f"{school['address']}, {school['city']}, representado por su Director/a.",
            "",
            f"De otra parte, D./Dña. {first} {last}, con DNI {dni},",
            f"nacido/a el {dob}, en calidad de trabajador/a.",
            "",
            "SEGUNDA: OBJETO DEL CONTRATO",
            "",
            f"El/La trabajador/a prestará sus servicios como {position}",
            f"en el centro educativo {school['name']},",
            "desempeñando las funciones propias del puesto docente.",
            "",
            "TERCERA: DURACIÓN Y JORNADA",
            "",
            f"Fecha de inicio: {datetime.now().strftime('%d/%m/%Y')}",
            "Tipo de contrato: Indefinido",
            "Jornada: Completa (lectiva según calendario escolar)",
            "",
            "CUARTA: RETRIBUCIÓN",
            "",
            f"Salario base mensual: {random.randint(1800, 2800):,} EUR",
            "Pagas extraordinarias: Dos anuales",
            "Retención IRPF según legislación vigente",
            "",
            "QUINTA: OBLIGACIONES",
            "",
            "El/La trabajador/a se compromete a:",
            "• Cumplir con el horario establecido",
            "• Impartir docencia según programación",
            "• Participar en actividades del centro",
            "• Mantener la titulación requerida",
        ]
        
        for line in content:
            if line.startswith("PRIMERA") or line.startswith("SEGUNDA") or \
               line.startswith("TERCERA") or line.startswith("CUARTA") or line.startswith("QUINTA"):
                draw.text((250, y), line, fill=(200, 16, 46), font=font_bold)
                y += 70
            elif line.startswith("•"):
                draw.text((350, y), line, fill=(60, 60, 60), font=font_normal)
                y += 52
            elif "Número de Contrato" in line:
                draw.text((w//2, y), line, fill=(0, 0, 0), font=font_bold, anchor="mm")
                y += 70
            elif line:
                draw.text((250, y), line, fill=(60, 60, 60), font=font_normal)
                y += 52
            else:
                y += 30
        
        # Signatures
        y = h - 500
        months_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", 
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        date_str = f"{datetime.now().day} de {months_es[datetime.now().month-1]} de {datetime.now().year}"
        
        draw.text((w//2, y), f"En {school['city']}, a {date_str}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        col1_x = 500
        col2_x = w - 500
        
        # Employer signature
        draw.text((col1_x, y), "EL EMPLEADOR", fill=(0, 0, 0), font=font_bold, anchor="mm")
        draw.text((col2_x, y), "EL/LA TRABAJADOR/A", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 100
        draw.line([(col1_x-150, y), (col1_x+150, y)], fill=(0, 0, 0), width=2)
        draw.line([(col2_x-150, y), (col2_x+150, y)], fill=(0, 0, 0), width=2)
        
        y += 45
        draw.text((col1_x, y), "Director/a del Centro", fill=(80, 80, 80), font=font_small, anchor="mm")
        draw.text((col2_x, y), f"{first} {last}", fill=(80, 80, 80), font=font_small, anchor="mm")
        
        y += 40
        draw.text((col2_x, y), f"DNI: {dni}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(200, 16, 46), width=3)
        y += 45
        draw.text((w//2, y), "Contrato sujeto a la legislación laboral española vigente", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
