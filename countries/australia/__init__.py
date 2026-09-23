"""
Australia data and document generators

Australian teacher verification requirements:
1. Signed School Letter
2. School ID
3. Teaching License
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar, load_font
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import random


# Australia Schools Database
DEFAULT_AUSTRALIA_SCHOOLS = [
    {"name": "Sydney Grammar School", "address": "College Street", "city": "Sydney", "state": "NSW", "postcode": "2000", "phone": "+61 2 9332 7700", "domain": "sydgram.nsw.edu.au"},
    {"name": "Melbourne High School", "address": "Forrest Hill", "city": "South Yarra", "state": "VIC", "postcode": "3141", "phone": "+61 3 9826 0711", "domain": "mhs.vic.edu.au"},
    {"name": "Brisbane Grammar School", "address": "Gregory Terrace", "city": "Brisbane", "state": "QLD", "postcode": "4000", "phone": "+61 7 3834 5200", "domain": "brisbanegrammar.com"},
    {"name": "Perth Modern School", "address": "Roberts Road", "city": "Subiaco", "state": "WA", "postcode": "6008", "phone": "+61 8 9380 0555", "domain": "perthmodern.wa.edu.au"},
    {"name": "Adelaide High School", "address": "West Terrace", "city": "Adelaide", "state": "SA", "postcode": "5000", "phone": "+61 8 8205 8200", "domain": "adelaide.sa.edu.au"},
    {"name": "Hobart College", "address": "Olinda Grove", "city": "Mount Nelson", "state": "TAS", "postcode": "7007", "phone": "+61 3 6220 8200", "domain": "hobart.college.tas.edu.au"},
    {"name": "Canberra Grammar School", "address": "Monaro Crescent", "city": "Red Hill", "state": "ACT", "postcode": "2603", "phone": "+61 2 6260 9700", "domain": "cgs.act.edu.au"},
    {"name": "James Ruse Agricultural High School", "address": "Felton Road", "city": "Carlingford", "state": "NSW", "postcode": "2118", "phone": "+61 2 9871 1566", "domain": "jamesruse.nsw.edu.au"},
    {"name": "Mac.Robertson Girls' High School", "address": "Kings Way", "city": "Melbourne", "state": "VIC", "postcode": "3004", "phone": "+61 3 9865 0900", "domain": "macrobertson.vic.edu.au"},
    {"name": "Brisbane State High School", "address": "Vulture Street", "city": "South Brisbane", "state": "QLD", "postcode": "4101", "phone": "+61 7 3513 5888", "domain": "brisbaneshs.eq.edu.au"},
]

# Australian Names
AUSTRALIA_FIRST_NAMES = [
    "Oliver", "Charlotte", "Jack", "Amelia", "Noah", "Mia", "William", "Olivia",
    "James", "Isla", "Lucas", "Ava", "Henry", "Chloe", "Thomas", "Emily",
    "Ethan", "Sophie", "Mason", "Grace", "Alexander", "Ruby", "Liam", "Ella",
    "Benjamin", "Zoe", "Samuel", "Lucy", "Daniel", "Harper", "Jackson", "Lily"
]

AUSTRALIA_LAST_NAMES = [
    "Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Anderson", "Thomas",
    "Roberts", "Johnson", "White", "Martin", "Thompson", "Walker", "Robinson", "Clarke",
    "Edwards", "Stewart", "King", "Murphy", "Kelly", "Baker", "Harris", "Young",
    "Mitchell", "Campbell", "Scott", "Watson", "Moore", "Lee", "Cooper", "Davis"
]

# Australian Teaching Positions
AUSTRALIA_TEACHING_POSITIONS = [
    "Mathematics Teacher",
    "English Teacher",
    "Science Teacher",
    "History Teacher",
    "Geography Teacher",
    "Physical Education Teacher",
    "Art Teacher",
    "Music Teacher",
    "Languages Teacher",
    "Technology Teacher",
    "STEM Coordinator",
    "Head of Department",
]


class AustraliaGenerator(CountryGenerator):
    """Australia-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Australia"
    
    def get_country_code(self) -> str:
        return "australia"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_AUSTRALIA_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return AUSTRALIA_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return AUSTRALIA_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return AUSTRALIA_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["signed_school_letter", "school_id", "teaching_license"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Australia document"""
        if doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        elif doc_type == "school_id":
            return self._generate_school_id(first, last, school, position, dob)
        elif doc_type == "teaching_license":
            return self._generate_teaching_license(first, last, school, position, dob)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 52)
        font_header = load_font('arialbd', 44)
        font_normal = load_font('arial', 38)
        font_bold = load_font('arialbd', 38)
        font_small = load_font('arial', 32)
        
        # Australian colors header (green and gold)
        draw.rectangle([(0, 0), (w, 60)], fill=(0, 120, 60))
        draw.rectangle([(0, 60), (w, 100)], fill=(255, 200, 0))
        
        # School header
        y = 160
        draw.text((w//2, y), school["name"].upper(), fill=(0, 120, 60), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['state']} {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Phone: {school['phone']} | Web: {school['domain']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+6)], fill=(0, 120, 60))
        
        # Title
        y += 100
        draw.text((w//2, y), "LETTER OF EMPLOYMENT", fill=(0, 120, 60), font=font_header, anchor="mm")
        
        # Date
        y += 100
        draw.text((w-300, y), datetime.now().strftime("%d %B %Y"), fill=(80, 80, 80), font=font_normal, anchor="rm")
        
        # Salutation
        y += 100
        draw.text((250, y), "To Whom It May Concern,", fill=(40, 40, 40), font=font_bold)
        
        # Body
        y += 100
        content_lines = [
            f"This letter is to confirm that {first} {last} is currently employed at",
            f"{school['name']} as a {position}.",
            "",
            f"{first} has been a valued member of our teaching staff since",
            f"{datetime.now().year - random.randint(2, 8)} and continues to demonstrate exceptional",
            "commitment to educational excellence and student development.",
            "",
            "Their responsibilities include:",
            f"• Teaching {position.replace(' Teacher', '')} to students across various year levels",
            "• Curriculum development and assessment design",
            "• Pastoral care and student mentoring",
            "• Collaboration with colleagues and school leadership",
            "",
            f"{first} holds current teacher registration with the relevant state authority",
            "and maintains all required qualifications and professional development.",
            "",
            "This letter is provided for official verification purposes.",
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
        draw.text((250, y), "Yours sincerely,", fill=(40, 40, 40), font=font_normal)
        
        y += 120
        draw.line([(250, y), (850, y)], fill=(0, 120, 60), width=3)
        y += 45
        draw.text((250, y), "Principal", fill=(0, 0, 0), font=font_bold)
        y += 50
        draw.text((250, y), school['name'], fill=(80, 80, 80), font=font_small)
        
        # School stamp placeholder
        stamp_x, stamp_y = 1800, y - 120
        draw.ellipse([(stamp_x-80, stamp_y-80), (stamp_x+80, stamp_y+80)], 
                    outline=(0, 120, 60), width=8)
        draw.text((stamp_x, stamp_y), "SCHOOL", fill=(0, 120, 60), font=font_bold, anchor="mm")
        draw.text((stamp_x, stamp_y+30), "SEAL", fill=(0, 120, 60), font=font_small, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(0, 120, 60), width=3)
        y += 45
        draw.text((w//2, y), f"Official document from {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_school_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate School ID Card"""
        w, h = 1280, 800
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 42)
        font_header = load_font('arialbd', 32)
        font_normal = load_font('arial', 26)
        font_bold = load_font('arialbd', 28)
        font_small = load_font('arial', 22)
        
        # Background gradient (green to gold)
        for i in range(h):
            alpha = i / h
            r = int(0 + (255 - 0) * alpha)
            g = int(120 + (200 - 120) * alpha)
            b = int(60 + (0 - 60) * alpha)
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        
        # White card area
        card_margin = 30
        draw.rectangle([(card_margin, card_margin), (w-card_margin, h-card_margin)], 
                      fill=(255, 255, 255), outline=(0, 120, 60), width=8)
        
        # Header
        y = 70
        draw.text((w//2, y), school["name"].upper(), fill=(0, 120, 60), font=font_title, anchor="mm")
        y += 50
        draw.text((w//2, y), "STAFF IDENTIFICATION CARD", fill=(255, 200, 0), font=font_header, anchor="mm")
        
        # Photo section
        photo_size = (220, 280)
        photo_x, photo_y = 80, 200
        
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(0, 120, 60))
        
        draw.rectangle([(photo_x-5, photo_y-5), (photo_x+photo_size[0]+5, photo_y+photo_size[1]+5)], 
                      outline=(0, 120, 60), width=4)
        img.paste(photo, (photo_x, photo_y))
        
        # Information section
        info_x = 340
        y = 220
        
        staff_id = f"STF{random.randint(10000, 99999)}"
        
        info_items = [
            ("NAME:", f"{first} {last}".upper()),
            ("POSITION:", position.upper()),
            ("STAFF ID:", staff_id),
            ("DEPARTMENT:", "Teaching Staff"),
            ("DATE OF BIRTH:", dob),
            ("VALID UNTIL:", f"{datetime.now().month:02d}/{datetime.now().year + 3}"),
        ]
        
        for label, value in info_items:
            draw.text((info_x, y), label, fill=(100, 100, 100), font=font_small)
            y += 32
            draw.text((info_x, y), value, fill=(0, 0, 0), font=font_bold)
            y += 50
        
        # Barcode placeholder
        barcode_y = h - 120
        draw.rectangle([(80, barcode_y), (w-80, barcode_y+60)], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        for i in range(20):
            x = 100 + i * 50
            width = random.choice([2, 4, 6, 8])
            draw.rectangle([(x, barcode_y+10), (x+width, barcode_y+50)], fill=(0, 0, 0))
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_license(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Teaching License/Registration Certificate"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 60)
        font_header = load_font('arialbd', 48)
        font_normal = load_font('arial', 38)
        font_bold = load_font('arialbd', 40)
        font_small = load_font('arial', 32)
        
        # Header with Australian colors
        draw.rectangle([(0, 0), (w, 80)], fill=(0, 120, 60))
        draw.rectangle([(0, 80), (w, 140)], fill=(255, 200, 0))
        
        # Title section
        y = 220
        draw.text((w//2, y), "TEACHER REGISTRATION CERTIFICATE", fill=(0, 120, 60), 
                 font=font_title, anchor="mm")
        y += 80
        draw.text((w//2, y), f"{school['state']} Teaching Authority", fill=(100, 100, 100), 
                 font=font_header, anchor="mm")
        
        # Certificate border
        border_margin = 100
        draw.rectangle([(border_margin, 400), (w-border_margin, h-300)], 
                      outline=(0, 120, 60), width=12)
        draw.rectangle([(border_margin+20, 420), (w-border_margin-20, h-320)], 
                      outline=(255, 200, 0), width=6)
        
        # Certificate content
        y = 550
        draw.text((w//2, y), "This is to certify that", fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w//2, y), f"{first} {last}".upper(), fill=(0, 120, 60), font=font_title, anchor="mm")
        
        y += 120
        registration_num = f"TRN{random.randint(100000, 999999)}"
        
        cert_lines = [
            "is a registered teacher in the state of " + school['state'],
            "",
            f"Registration Number: {registration_num}",
            f"Date of Birth: {dob}",
            "",
            "This certificate confirms that the holder:",
            "• Meets all professional teaching standards",
            "• Holds approved qualifications in education",
            "• Has completed all required background checks",
            "• Is authorized to teach in " + school['state'] + " schools",
            "",
            f"Current Position: {position}",
            f"Current School: {school['name']}",
        ]
        
        for line in cert_lines:
            if line.startswith("•"):
                draw.text((w//2 - 300, y), line, fill=(60, 60, 60), font=font_normal)
                y += 60
            elif "Registration Number" in line or "Date of Birth" in line:
                draw.text((w//2, y), line, fill=(0, 0, 0), font=font_bold, anchor="mm")
                y += 70
            elif line:
                draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
                y += 60
            else:
                y += 40
        
        # Validity section
        y += 80
        issue_date = datetime.now().strftime("%d %B %Y")
        expiry_date = f"{datetime.now().day} {datetime.now().strftime('%B')} {datetime.now().year + 5}"
        
        draw.rectangle([(300, y), (w-300, y+200)], fill=(250, 250, 245), outline=(0, 120, 60), width=4)
        y += 60
        draw.text((w//2, y), f"Date of Issue: {issue_date}", fill=(0, 120, 60), font=font_bold, anchor="mm")
        y += 70
        draw.text((w//2, y), f"Valid Until: {expiry_date}", fill=(0, 120, 60), font=font_bold, anchor="mm")
        
        # Official seal
        seal_x, seal_y = w//2, h - 450
        draw.ellipse([(seal_x-100, seal_y-100), (seal_x+100, seal_y+100)], 
                    outline=(0, 120, 60), width=10)
        draw.ellipse([(seal_x-80, seal_y-80), (seal_x+80, seal_y+80)], 
                    outline=(255, 200, 0), width=6)
        draw.text((seal_x, seal_y-20), "OFFICIAL", fill=(0, 120, 60), font=font_bold, anchor="mm")
        draw.text((seal_x, seal_y+20), "SEAL", fill=(0, 120, 60), font=font_bold, anchor="mm")
        
        # Signature
        y = h - 280
        draw.text((w//2, y), "________________________", fill=(0, 0, 0), font=font_normal, anchor="mm")
        y += 60
        draw.text((w//2, y), "Registrar, Teaching Authority", fill=(80, 80, 80), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
