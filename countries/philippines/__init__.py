"""
Philippines data and document generators

Filipino teacher verification requirements:
1. Teaching ID (Professional Teacher's ID)
2. Signed School Letter (Certificate of Employment)
3. Teaching License (Professional Regulation Commission License)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Philippines Universities Database
DEFAULT_PHILIPPINES_SCHOOLS = [
    {"name": "Ateneo de Manila Grade School", "address": "Katipunan Avenue, Loyola Heights", "city": "Quezon City", "region": "Metro Manila", "postcode": "1108", "phone": "+63 2 8426 6001", "domain": "ateneo.edu"},
    {"name": "De La Salle Santiago Zobel School", "address": "University Avenue, Ayala Alabang", "city": "Muntinlupa", "region": "Metro Manila", "postcode": "1780", "phone": "+63 2 8771 3579", "domain": "dlszobel.edu.ph"},
    {"name": "Xavier School", "address": "64 Xavier Street, Greenhills West", "city": "San Juan", "region": "Metro Manila", "postcode": "1503", "phone": "+63 2 8721 2477", "domain": "xs.edu.ph"},
    {"name": "Saint Jude Catholic School", "address": "327 Don Quijote Street", "city": "Manila", "region": "Metro Manila", "postcode": "1008", "phone": "+63 2 8741 0231", "domain": "sjcs.edu.ph"},
    {"name": "Miriam College Grade School", "address": "Katipunan Avenue, Loyola Heights", "city": "Quezon City", "region": "Metro Manila", "postcode": "1108", "phone": "+63 2 8580 5400", "domain": "mc.edu.ph"},
    {"name": "Saint Pedro Poveda College", "address": "EDSA corner Poveda Lane", "city": "Quezon City", "region": "Metro Manila", "postcode": "1605", "phone": "+63 2 8631 8756", "domain": "poveda.edu.ph"},
    {"name": "British School Manila", "address": "36th Street, University Park", "city": "Taguig", "region": "Metro Manila", "postcode": "1634", "phone": "+63 2 8860 4800", "domain": "britishschoolmanila.org"},
    {"name": "International School Manila", "address": "University Parkway, Bonifacio Global City", "city": "Taguig", "region": "Metro Manila", "postcode": "1634", "phone": "+63 2 8840 8400", "domain": "ismanila.org"},
    {"name": "Reedley International School", "address": "1 Notre Dame Avenue, Pasig", "city": "Pasig", "region": "Metro Manila", "postcode": "1606", "phone": "+63 2 8635 9669", "domain": "reedleyschool.edu.ph"},
    {"name": "Assumption College San Lorenzo", "address": "San Lorenzo Drive, Makati", "city": "Makati", "region": "Metro Manila", "postcode": "1223", "phone": "+63 2 8817 0757", "domain": "assumption.edu.ph"},
    {"name": "Saint Paul College Pasig", "address": "C-5 Road, Bagong Ilog", "city": "Pasig", "region": "Metro Manila", "postcode": "1600", "phone": "+63 2 8671 2940", "domain": "spcp.edu.ph"},
    {"name": "Colegio San Agustin Makati", "address": "6000 Dasmariñas Village", "city": "Makati", "region": "Metro Manila", "postcode": "1222", "phone": "+63 2 8810 6781", "domain": "csa-makati.edu.ph"},
    {"name": "Brent International School Manila", "address": "Brent Road", "city": "Biñan", "region": "Laguna", "postcode": "4024", "phone": "+63 49 511 4330", "domain": "brent.edu.ph"},
    {"name": "Cebu International School", "address": "Pit-os, Talamban", "city": "Cebu City", "region": "Cebu", "postcode": "6000", "phone": "+63 32 401 1900", "domain": "cis.edu.ph"},
    {"name": "Saint Scholastica's College Manila", "address": "2560 Leon Guinto Street", "city": "Manila", "region": "Metro Manila", "postcode": "1004", "phone": "+63 2 8567 7686", "domain": "ssc.edu.ph"},
]

# Filipino Names
PHILIPPINES_FIRST_NAMES = [
    "Maria", "Jose", "Juan", "Antonio", "Pedro", "Francisco", "Manuel", "Luis",
    "Ana", "Carmen", "Teresa", "Rosa", "Josefa", "Juana", "Francisca", "Isabel",
    "Miguel", "Jorge", "Carlos", "Roberto", "Fernando", "Eduardo", "Ricardo", "Alberto",
    "Luz", "Angelica", "Remedios", "Rosario", "Gloria", "Concepcion", "Pilar", "Mercedes"
]

PHILIPPINES_LAST_NAMES = [
    "Santos", "Reyes", "Cruz", "Bautista", "Ocampo", "Garcia", "Mendoza", "Torres",
    "Lopez", "Gonzales", "Flores", "Rivera", "Ramos", "Castillo", "Del Rosario", "Hernandez",
    "Aquino", "Fernandez", "Valdez", "Villanueva", "Perez", "Sanchez", "Ramirez", "Alvarez",
    "Morales", "Diaz", "Romero", "Gutierrez", "Santiago", "Salazar", "Jimenez", "De Leon"
]

# Filipino K-12 Teaching Positions (Kindergarten, Elementary, Junior HS, Senior HS)
PHILIPPINES_TEACHING_POSITIONS = [
    "Kindergarten Teacher",
    "Preschool Teacher",
    "Grade School Teacher",
    "Elementary Teacher I",
    "Elementary Teacher II",
    "English Teacher - Elementary",
    "Math Teacher - Elementary",
    "Filipino Teacher",
    "Araling Panlipunan Teacher",
    "MAPEH Teacher",
    "Junior High School Teacher - Mathematics",
    "Junior High School Teacher - Science",
    "Junior High School Teacher - English",
    "Senior High School Teacher - STEM",
    "Senior High School Teacher - HUMSS",
    "Senior High School Teacher - ABM",
    "Class Adviser",
    "Guidance Counselor",
    "Subject Coordinator",
    "Grade Level Coordinator",
]


class PhilippinesGenerator(CountryGenerator):
    """Philippines-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Philippines"
    
    def get_country_code(self) -> str:
        return "philippines"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_PHILIPPINES_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return PHILIPPINES_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return PHILIPPINES_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return PHILIPPINES_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["teaching_id", "employment_certificate", "teaching_license"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Philippines document"""
        if doc_type == "teaching_id":
            return self._generate_teaching_id(first, last, school, position, dob)
        elif doc_type == "employment_certificate":
            return self._generate_employment_certificate(first, last, school, position)
        elif doc_type == "teaching_license":
            return self._generate_teaching_license(first, last, school, position, dob)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_teaching_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Filipino Teaching ID Card"""
        # Create image 1000x630 pixels
        img = Image.new('RGB', (1000, 630), color='white')
        draw = ImageDraw.Draw(img)
        
        # Colors - Filipino flag colors
        header_color = (0, 56, 168)  # Blue
        accent_color = (206, 17, 38)  # Red
        text_color = (0, 0, 0)
        
        # Draw header
        draw.rectangle([0, 0, 1000, 120], fill=header_color)
        
        # Title
        title_font = load_font(42, bold=True)
        draw.text((500, 60), "PROFESSIONAL TEACHER'S ID", font=title_font, fill='white', anchor='mm')
        
        # Red accent stripe
        draw.rectangle([0, 120, 1000, 130], fill=accent_color)
        
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
        draw.text((280, y_pos), "NAME:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), f"{first} {last}", font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Position
        draw.text((280, y_pos), "POSITION:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), position, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # School
        draw.text((280, y_pos), "INSTITUTION:", font=info_font, fill=text_color)
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
        id_number = f"PH-{random.randint(100000, 999999)}"
        draw.text((280, y_pos), "ID NUMBER:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), id_number, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Issue date
        issue_date = datetime.now().strftime("%B %d, %Y")
        draw.text((280, y_pos), "DATE ISSUED:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 25), issue_date, font=value_font, fill=text_color)
        
        # Footer
        footer_font = load_font(16)
        draw.text((500, 600), "DepEd - Department of Education, Republic of the Philippines", 
                 font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_employment_certificate(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Certificate of Employment"""
        # Create image 1000x1400 pixels (letter size)
        img = Image.new('RGB', (1000, 1400), color='white')
        draw = ImageDraw.Draw(img)
        
        text_color = (0, 0, 0)
        header_color = (0, 56, 168)
        
        # Header with color
        draw.rectangle([0, 0, 1000, 150], fill=header_color)
        
        header_font = load_font(36, bold=True)
        draw.text((500, 75), "CERTIFICATE OF EMPLOYMENT", font=header_font, fill='white', anchor='mm')
        
        # School letterhead
        school_font = load_font(28, bold=True)
        info_font = load_font(18)
        
        draw.text((500, 220), school['name'], font=school_font, fill=text_color, anchor='mm')
        draw.text((500, 260), f"{school['address']}", font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 290), f"{school['city']}, {school['region']}, Philippines", 
                 font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 320), f"Tel: {school['phone']}", font=info_font, fill=text_color, anchor='mm')
        
        # Draw line
        draw.line([100, 360, 900, 360], fill=text_color, width=2)
        
        # Date
        date_font = load_font(20)
        current_date = datetime.now().strftime("%B %d, %Y")
        draw.text((800, 400), current_date, font=date_font, fill=text_color, anchor='rm')
        
        # Letter title
        title_font = load_font(24, bold=True)
        draw.text((500, 460), "TO WHOM IT MAY CONCERN:", font=title_font, fill=text_color, anchor='mm')
        
        # Letter body
        body_font = load_font(20)
        y_pos = 530
        line_spacing = 35
        
        lines = [
            f"This is to certify that {first} {last} has been employed",
            f"at {school['name']} as {position}",
            f"since {datetime.now().year - random.randint(1, 5)}.",
            "",
            "During his/her tenure with our institution, he/she has demonstrated",
            "exemplary performance in teaching, dedication to student development,",
            "and active participation in school activities and programs.",
            "",
            "His/Her duties and responsibilities include:",
            "",
            "• Preparation and delivery of lessons in accordance with curriculum",
            "• Assessment and evaluation of student performance",
            "• Participation in faculty meetings and professional development",
            "• Collaboration with colleagues and school administration",
            "",
            "This certification is being issued upon the request of the above-named",
            "for whatever legal purpose it may serve.",
            "",
            "Issued this " + datetime.now().strftime("%d day of %B, %Y."),
        ]
        
        for line in lines:
            if line.startswith("•"):
                draw.text((120, y_pos), line, font=body_font, fill=text_color)
            else:
                draw.text((100, y_pos), line, font=body_font, fill=text_color)
            y_pos += line_spacing
        
        # Signatures
        y_pos += 50
        draw.line([150, y_pos, 450, y_pos], fill=text_color, width=2)
        draw.line([550, y_pos, 850, y_pos], fill=text_color, width=2)
        
        sig_font = load_font(16, bold=True)
        draw.text((300, y_pos + 20), "Principal/Director", font=sig_font, fill=text_color, anchor='mm')
        draw.text((700, y_pos + 20), "HR Officer", font=sig_font, fill=text_color, anchor='mm')
        
        # School seal placeholder
        draw.ellipse([400, y_pos - 100, 600, y_pos + 10], outline=text_color, width=3)
        seal_font = load_font(16)
        draw.text((500, y_pos - 45), "OFFICIAL", font=seal_font, fill=text_color, anchor='mm')
        draw.text((500, y_pos - 25), "SEAL", font=seal_font, fill=text_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 1350), "This is a computer-generated document. Valid without signature if digitally signed.", 
                 font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_license(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate PRC Teaching License"""
        # Create image 1000x630 pixels
        img = Image.new('RGB', (1000, 630), color='white')
        draw = ImageDraw.Draw(img)
        
        # Colors
        header_color = (0, 56, 168)
        accent_color = (206, 17, 38)
        text_color = (0, 0, 0)
        
        # Draw header
        draw.rectangle([0, 0, 1000, 140], fill=header_color)
        
        # PRC Logo area (placeholder)
        draw.ellipse([30, 30, 130, 130], fill='white', outline=accent_color, width=3)
        prc_font = load_font(16, bold=True)
        draw.text((80, 80), "PRC", font=prc_font, fill=header_color, anchor='mm')
        
        # Title
        title_font = load_font(36, bold=True)
        subtitle_font = load_font(20)
        draw.text((550, 50), "PROFESSIONAL REGULATION COMMISSION", font=title_font, fill='white', anchor='mm')
        draw.text((550, 85), "Republic of the Philippines", font=subtitle_font, fill='white', anchor='mm')
        draw.text((550, 110), "PROFESSIONAL TEACHER LICENSE", font=subtitle_font, fill='white', anchor='mm')
        
        # Red stripe
        draw.rectangle([0, 140, 1000, 150], fill=accent_color)
        
        # Photo
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(person_id=person_id, gender=gender)
        if photo:
            photo = photo.resize((180, 220))
            img.paste(photo, (60, 180))
        else:
            draw.rectangle([60, 180, 240, 400], fill=(200, 200, 200))
            avatar = generate_initials_avatar(first, last, size=180)
            img.paste(avatar, (60, 180))
        
        # License Information
        info_font = load_font(22, bold=True)
        value_font = load_font(20)
        
        y_pos = 190
        spacing = 45
        
        # License Number
        license_no = f"LET-{random.randint(100000, 999999)}"
        draw.text((270, y_pos), "LICENSE NO:", font=info_font, fill=text_color)
        draw.text((270, y_pos + 25), license_no, font=value_font, fill=accent_color)
        
        y_pos += spacing + 10
        
        # Name
        draw.text((270, y_pos), "NAME:", font=info_font, fill=text_color)
        draw.text((270, y_pos + 25), f"{first} {last}".upper(), font=value_font, fill=text_color)
        
        y_pos += spacing + 5
        
        # Date of Birth
        draw.text((270, y_pos), "DATE OF BIRTH:", font=info_font, fill=text_color)
        draw.text((270, y_pos + 25), dob, font=value_font, fill=text_color)
        
        y_pos += spacing + 5
        
        # Registration Date
        reg_date = datetime.now().strftime("%B %d, %Y")
        draw.text((270, y_pos), "DATE REGISTERED:", font=info_font, fill=text_color)
        draw.text((270, y_pos + 25), reg_date, font=value_font, fill=text_color)
        
        y_pos += spacing + 5
        
        # Validity
        validity_year = datetime.now().year + 3
        draw.text((270, y_pos), "VALID UNTIL:", font=info_font, fill=text_color)
        draw.text((270, y_pos + 25), f"December 31, {validity_year}", font=value_font, fill=text_color)
        
        # Signature area
        y_pos = 480
        draw.line([60, y_pos, 240, y_pos], fill=text_color, width=2)
        sig_font = load_font(14)
        draw.text((150, y_pos + 10), "License Holder", font=sig_font, fill=text_color, anchor='mm')
        
        draw.line([700, y_pos, 900, y_pos], fill=text_color, width=2)
        draw.text((800, y_pos + 10), "PRC Commissioner", font=sig_font, fill=text_color, anchor='mm')
        
        # QR Code placeholder with pattern
        qr_size = 130
        qr_x, qr_y = 650, 200
        draw.rectangle([qr_x, qr_y, qr_x + qr_size, qr_y + qr_size], fill='white', outline=text_color, width=2)
        
        # Draw QR-like pattern
        block_size = 6
        for i in range(0, qr_size, block_size):
            for j in range(0, qr_size, block_size):
                if random.choice([True, False]):
                    draw.rectangle(
                        [qr_x + i, qr_y + j, qr_x + i + block_size - 1, qr_y + j + block_size - 1],
                        fill=text_color
                    )
        
        # Corner squares (typical QR code markers)
        corner_size = 20
        for cx, cy in [(qr_x + 5, qr_y + 5), (qr_x + qr_size - corner_size - 5, qr_y + 5), (qr_x + 5, qr_y + qr_size - corner_size - 5)]:
            draw.rectangle([cx, cy, cx + corner_size, cy + corner_size], outline=text_color, width=2)
            draw.rectangle([cx + 6, cy + 6, cx + corner_size - 6, cy + corner_size - 6], fill=text_color)
        
        # Verification text
        verify_font = load_font(12)
        draw.text((715, 350), "Scan to verify", font=verify_font, fill=text_color, anchor='mm')
        draw.text((715, 370), "at prc.gov.ph", font=verify_font, fill=text_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 560), "This license is valid throughout the Philippines", 
                 font=footer_font, fill=text_color, anchor='mm')
        draw.text((500, 590), "WARNING: Any alteration or unauthorized use of this license is punishable by law", 
                 font=footer_font, fill=accent_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


# Create generator instance
generator = PhilippinesGenerator()
