"""
Canada data and document generators

Canadian teacher verification requirements:
1. OCT Card (Ontario College of Teachers)
2. Teaching License
3. Signed School Letter
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Canada Schools Database
DEFAULT_CANADA_SCHOOLS = [
    {"name": "Upper Canada College", "address": "200 Lonsdale Road", "city": "Toronto", "province": "Ontario", "postcode": "M4V 1W6", "phone": "+1 416-488-1125", "domain": "ucc.on.ca"},
    {"name": "St. George's School", "address": "4175 West 29th Avenue", "city": "Vancouver", "province": "British Columbia", "postcode": "V6S 1V1", "phone": "+1 604-221-3939", "domain": "stgeorges.bc.ca"},
    {"name": "Collège Jean-de-Brébeuf", "address": "3200 Chemin de la Côte-Sainte-Catherine", "city": "Montréal", "province": "Québec", "postcode": "H3T 1C1", "phone": "+1 514-342-9342", "domain": "brebeuf.qc.ca"},
    {"name": "Appleby College", "address": "540 Lakeshore Road West", "city": "Oakville", "province": "Ontario", "postcode": "L6K 3P1", "phone": "+1 905-845-4681", "domain": "appleby.on.ca"},
    {"name": "Strathcona-Tweedsmuir School", "address": "RR2", "city": "Okotoks", "province": "Alberta", "postcode": "T1S 1A2", "phone": "+1 403-938-4431", "domain": "sts.ab.ca"},
    {"name": "Bishop's College School", "address": "80 Chemin Moulton Hill", "city": "Sherbrooke", "province": "Québec", "postcode": "J1M 1Z8", "phone": "+1 819-566-0227", "domain": "bishopscollegeschool.com"},
    {"name": "Havergal College", "address": "1451 Avenue Road", "city": "Toronto", "province": "Ontario", "postcode": "M5N 2H9", "phone": "+1 416-483-3519", "domain": "havergal.on.ca"},
    {"name": "St. John's-Ravenscourt School", "address": "400 South Drive", "city": "Winnipeg", "province": "Manitoba", "postcode": "R3T 3K5", "phone": "+1 204-477-2400", "domain": "sjr.mb.ca"},
    {"name": "Lakefield College School", "address": "4391 County Road 29", "city": "Lakefield", "province": "Ontario", "postcode": "K0L 2H0", "phone": "+1 705-652-3324", "domain": "lcs.on.ca"},
    {"name": "Brentwood College School", "address": "2735 Mt. Baker Road", "city": "Mill Bay", "province": "British Columbia", "postcode": "V0R 2P1", "phone": "+1 250-743-5521", "domain": "brentwood.bc.ca"},
]

# Canadian Names
CANADA_FIRST_NAMES = [
    "Liam", "Emma", "Noah", "Olivia", "William", "Ava", "James", "Sophia",
    "Benjamin", "Isabella", "Lucas", "Mia", "Ethan", "Charlotte", "Alexander", "Amelia",
    "Jacob", "Emily", "Michael", "Harper", "Daniel", "Evelyn", "Matthew", "Abigail",
    "Jackson", "Ella", "Logan", "Grace", "David", "Lily", "Samuel", "Chloe",
    "Émile", "Amélie", "Antoine", "Léa"
]

CANADA_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark",
    "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
    "Tremblay", "Gagnon", "Roy", "Côté", "Bouchard", "Gauthier", "Morin", "Lavoie"
]

# Canadian Teaching Positions
CANADA_TEACHING_POSITIONS = [
    "Mathematics Teacher",
    "English/Language Arts Teacher",
    "French Immersion Teacher",
    "Science Teacher",
    "Social Studies Teacher",
    "Physical Education Teacher",
    "Arts Teacher",
    "Music Teacher",
    "Special Education Teacher",
    "ESL/ELL Teacher",
    "STEM Coordinator",
    "Department Head",
]


class CanadaGenerator(CountryGenerator):
    """Canada-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Canada"
    
    def get_country_code(self) -> str:
        return "canada"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_CANADA_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return CANADA_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return CANADA_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return CANADA_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["oct_card", "teaching_license", "signed_school_letter"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Canada document"""
        if doc_type == "oct_card":
            return self._generate_oct_card(first, last, school, position, dob)
        elif doc_type == "teaching_license":
            return self._generate_teaching_license(first, last, school, position, dob)
        elif doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_oct_card(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate OCT Card (Ontario College of Teachers)"""
        w, h = 1280, 800
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 40)
            font_header = load_font("arialbd", 32)
            font_normal = load_font("arial", 26)
            font_bold = load_font("arialbd", 28)
            font_small = load_font("arial", 22)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Red background (Canadian flag color)
        draw.rectangle([(0, 0), (w, h)], fill=(220, 30, 40))
        
        # White card area
        card_margin = 35
        draw.rectangle([(card_margin, card_margin), (w-card_margin, h-card_margin)], 
                      fill=(255, 255, 255), outline=(220, 30, 40), width=6)
        
        # Header
        y = 65
        draw.text((w//2, y), "ONTARIO COLLEGE OF TEACHERS", fill=(220, 30, 40), 
                 font=font_title, anchor="mm")
        y += 45
        draw.text((w//2, y), "ORDRE DES ENSEIGNANTES ET DES ENSEIGNANTS DE L'ONTARIO", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        y += 40
        draw.line([(80, y), (w-80, y)], fill=(220, 30, 40), width=3)
        
        # Photo section
        photo_size = (200, 250)
        photo_x, photo_y = 90, 200
        
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(220, 30, 40))
        
        draw.rectangle([(photo_x-4, photo_y-4), (photo_x+photo_size[0]+4, photo_y+photo_size[1]+4)], 
                      outline=(220, 30, 40), width=3)
        img.paste(photo, (photo_x, photo_y))
        
        # Information section
        info_x = 330
        y = 210
        
        oct_number = f"{random.randint(100000, 999999)}"
        
        info_items = [
            ("MEMBER NAME:", f"{first} {last}".upper()),
            ("OCT NUMBER:", oct_number),
            ("DATE OF BIRTH:", dob),
            ("QUALIFICATIONS:", "Bachelor of Education"),
            ("MEMBER TYPE:", "Registered Teacher"),
            ("STATUS:", "Active - In Good Standing"),
            ("EXPIRY DATE:", f"{datetime.now().strftime('%B %d')}, {datetime.now().year + 5}"),
        ]
        
        for label, value in info_items:
            draw.text((info_x, y), label, fill=(100, 100, 100), font=font_small)
            y += 28
            draw.text((info_x, y), value, fill=(0, 0, 0), font=font_bold)
            y += 48
        
        # Maple leaf symbol (simple representation)
        leaf_x, leaf_y = w - 150, h - 150
        draw.text((leaf_x, leaf_y), "🍁", fill=(220, 30, 40), font=font_title, anchor="mm")
        
        # Footer
        y = h - 80
        draw.text((w//2, y), "This card certifies membership in good standing", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_license(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Teaching License Certificate"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 60)
            font_header = load_font("arialbd", 48)
            font_normal = load_font("arial", 38)
            font_bold = load_font("arialbd", 40)
            font_small = load_font("arial", 32)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Canadian flag colors header
        draw.rectangle([(0, 0), (w, 100)], fill=(220, 30, 40))
        
        # Title section
        y = 200
        draw.text((w//2, y), "CERTIFICATE OF QUALIFICATION", fill=(220, 30, 40), 
                 font=font_title, anchor="mm")
        y += 70
        draw.text((w//2, y), "Teaching License", fill=(100, 100, 100), 
                 font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), school['province'], fill=(100, 100, 100), 
                 font=font_header, anchor="mm")
        
        # Certificate border
        border_margin = 120
        draw.rectangle([(border_margin, 450), (w-border_margin, h-350)], 
                      outline=(220, 30, 40), width=12)
        draw.rectangle([(border_margin+20, 470), (w-border_margin-20, h-370)], 
                      outline=(100, 100, 100), width=4)
        
        # Certificate content
        y = 600
        draw.text((w//2, y), "This certifies that", fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w//2, y), f"{first} {last}".upper(), fill=(220, 30, 40), font=font_title, anchor="mm")
        
        y += 120
        license_num = f"TC{random.randint(100000, 999999)}"
        
        cert_lines = [
            f"License Number: {license_num}",
            "",
            "has met all requirements for teacher certification in the",
            f"Province of {school['province']} and is hereby licensed to teach",
            "in accordance with provincial education regulations.",
            "",
            "This license confirms:",
            "• Completion of approved teacher education program",
            "• Successful criminal background verification",
            "• Adherence to professional teaching standards",
            "• Current knowledge of curriculum and pedagogy",
            "",
            f"Current Position: {position}",
            f"Current School: {school['name']}",
            f"Date of Birth: {dob}",
        ]
        
        for line in cert_lines:
            if line.startswith("•"):
                draw.text((w//2 - 400, y), line, fill=(60, 60, 60), font=font_normal)
                y += 60
            elif "License Number" in line:
                draw.text((w//2, y), line, fill=(0, 0, 0), font=font_bold, anchor="mm")
                y += 80
            elif line:
                draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
                y += 60
            else:
                y += 40
        
        # Validity section
        y += 70
        issue_date = datetime.now().strftime("%B %d, %Y")
        expiry_date = f"{datetime.now().strftime('%B %d')}, {datetime.now().year + 5}"
        
        draw.rectangle([(350, y), (w-350, y+180)], fill=(250, 248, 248), outline=(220, 30, 40), width=4)
        y += 55
        draw.text((w//2, y), f"Date of Issue: {issue_date}", fill=(220, 30, 40), font=font_bold, anchor="mm")
        y += 65
        draw.text((w//2, y), f"Valid Through: {expiry_date}", fill=(220, 30, 40), font=font_bold, anchor="mm")
        
        # Official seal
        seal_x, seal_y = w//2, h - 480
        draw.ellipse([(seal_x-100, seal_y-100), (seal_x+100, seal_y+100)], 
                    outline=(220, 30, 40), width=10)
        draw.text((seal_x, seal_y), "OFFICIAL", fill=(220, 30, 40), font=font_bold, anchor="mm")
        
        # Signature
        y = h - 300
        draw.line([(w//2-300, y), (w//2+300, y)], fill=(0, 0, 0), width=3)
        y += 50
        draw.text((w//2, y), f"Registrar, {school['province']} Teaching Authority", 
                 fill=(80, 80, 80), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter"""
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
        
        # Canadian red header
        draw.rectangle([(0, 0), (w, 80)], fill=(220, 30, 40))
        
        # School header
        y = 150
        draw.text((w//2, y), school["name"].upper(), fill=(220, 30, 40), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Phone: {school['phone']} | Web: {school['domain']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+6)], fill=(220, 30, 40))
        
        # Title
        y += 100
        draw.text((w//2, y), "EMPLOYMENT VERIFICATION LETTER", fill=(220, 30, 40), 
                 font=font_header, anchor="mm")
        
        # Date
        y += 100
        draw.text((w-300, y), datetime.now().strftime("%B %d, %Y"), 
                 fill=(80, 80, 80), font=font_normal, anchor="rm")
        
        # Salutation
        y += 100
        draw.text((250, y), "To Whom It May Concern,", fill=(40, 40, 40), font=font_bold)
        
        # Body
        y += 100
        content_lines = [
            f"This letter serves to confirm that {first} {last} is currently employed",
            f"at {school['name']} in the position of {position}.",
            "",
            f"{first} has been a member of our teaching staff since",
            f"{datetime.now().year - random.randint(2, 8)} and maintains an active teaching position.",
            "",
            "Professional Responsibilities:",
            f"• Instruction in {position.replace(' Teacher', '')}",
            "• Curriculum planning and student assessment",
            "• Student support and mentorship",
            "• Professional collaboration and development",
            "",
            f"{first} holds valid teacher certification with the {school['province']}",
            "teaching regulatory body and meets all provincial requirements for",
            "professional practice.",
            "",
            "This letter is issued for official verification purposes.",
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
        draw.text((250, y), "Sincerely,", fill=(40, 40, 40), font=font_normal)
        
        y += 120
        draw.line([(250, y), (850, y)], fill=(220, 30, 40), width=3)
        y += 45
        draw.text((250, y), "Head of School", fill=(0, 0, 0), font=font_bold)
        y += 50
        draw.text((250, y), school['name'], fill=(80, 80, 80), font=font_small)
        
        # School stamp
        stamp_x, stamp_y = 1800, y - 120
        draw.ellipse([(stamp_x-80, stamp_y-80), (stamp_x+80, stamp_y+80)], 
                    outline=(220, 30, 40), width=8)
        draw.text((stamp_x, stamp_y), "OFFICIAL", fill=(220, 30, 40), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(220, 30, 40), width=3)
        y += 45
        draw.text((w//2, y), f"Official correspondence from {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
