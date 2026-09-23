"""
UK (United Kingdom) data and document generators
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar, load_font
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import random


# UK Schools Database
DEFAULT_UK_SCHOOLS = [
    {"name": "Leeds Grammar School", "address": "Alwoodley Gates, Harrogate Road", "town": "Leeds", "postcode": "LS17 8GS", "phone": "0139 1219 502", "lea": "Leeds LEA"},
    {"name": "Manchester Grammar School", "address": "Old Hall Lane", "town": "Manchester", "postcode": "M13 0XT", "phone": "0161 224 7201", "lea": "Manchester LEA"},
    {"name": "King Edward's School", "address": "Edgbaston Park Road", "town": "Birmingham", "postcode": "B15 2UA", "phone": "0121 472 1672", "lea": "Birmingham LEA"},
    {"name": "St Paul's School", "address": "Lonsdale Road", "town": "London", "postcode": "SW13 9JT", "phone": "020 8748 9162", "lea": "Richmond LEA"},
    {"name": "Westminster School", "address": "Little Dean's Yard", "town": "London", "postcode": "SW1P 3PF", "phone": "020 7963 1000", "lea": "Westminster LEA"},
    {"name": "Eton College", "address": "High Street", "town": "Windsor", "postcode": "SL4 6DW", "phone": "01753 370 100", "lea": "Windsor LEA"},
    {"name": "Harrow School", "address": "5 High Street", "town": "Harrow", "postcode": "HA1 3HP", "phone": "020 8872 8000", "lea": "Harrow LEA"},
    {"name": "Rugby School", "address": "Lawrence Sheriff Street", "town": "Rugby", "postcode": "CV22 5EH", "phone": "01788 556 216", "lea": "Warwickshire LEA"},
    {"name": "Cheltenham Ladies' College", "address": "Bayshill Road", "town": "Cheltenham", "postcode": "GL50 3EP", "phone": "01242 520 691", "lea": "Gloucestershire LEA"},
    {"name": "Dulwich College", "address": "Dulwich Common", "town": "London", "postcode": "SE21 7LD", "phone": "020 8693 3601", "lea": "Southwark LEA"},
]

# UK Names
UK_FIRST_NAMES = [
    "James", "Oliver", "Harry", "George", "Noah", "Jack", "Charlie", "Oscar",
    "William", "Henry", "Thomas", "Alfie", "Joshua", "Leo", "Archie", "Ethan",
    "Emma", "Olivia", "Amelia", "Isla", "Ava", "Mia", "Emily", "Isabella",
    "Sophia", "Grace", "Lily", "Chloe", "Ella", "Charlotte", "Sophie", "Alice",
    "Angela", "David", "Michael", "Sarah", "Claire", "Andrew", "Peter", "Susan"
]

UK_LAST_NAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson",
    "Thomas", "Roberts", "Johnson", "Lewis", "Walker", "Robinson", "Wood", "Thompson",
    "White", "Watson", "Jackson", "Wright", "Green", "Harris", "Cooper", "King",
    "Lee", "Martin", "Clarke", "James", "Morgan", "Hughes", "Edwards", "Hill"
]

# UK Teaching Positions
UK_TEACHING_POSITIONS = [
    "Head of Drama Department",
    "Head of English Department", 
    "Head of Mathematics Department",
    "Head of Science Department",
    "Head of History Department",
    "Head of Geography Department",
    "Head of Modern Languages",
    "Head of Art Department",
    "Head of Music Department",
    "Head of PE Department",
    "Deputy Head Teacher",
    "Senior Teacher",
    "Class Teacher",
    "Subject Leader - English",
    "Subject Leader - Mathematics",
    "Year Group Leader",
]


class UKGenerator(CountryGenerator):
    """UK-specific document generator"""
    
    def get_country_name(self) -> str:
        return "United Kingdom"
    
    def get_country_code(self) -> str:
        return "uk"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_UK_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return UK_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return UK_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return UK_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["employment_letter", "teacher_id", "teaching_license"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate UK document"""
        if doc_type == "employment_letter":
            return self._generate_employment_letter(first, last, school, position)
        elif doc_type == "teacher_id":
            return self._generate_teacher_id(first, last, school, position, dob)
        elif doc_type == "teaching_license":
            return self._generate_teaching_license(first, last)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_employment_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Employment Letter from scratch"""
        # A4 size at 300 DPI
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        from ..utils import load_font
        
        font_logo = load_font('arialbd', 68)
        font_title = load_font('arialbd', 52)
        font_header = load_font('arialbd', 42)
        font_normal = load_font('arial', 35)
        font_bold = load_font('arialbd', 35)
        font_small = load_font('arial', 30)
        font_tiny = load_font('arial', 26)
        
        current_date = datetime.now().strftime("%d %B %Y")
        data_controller = f"Z{random.randint(1000000, 9999999)}"
        ref_number = f"EMP/{random.randint(1000, 9999)}/{datetime.now().year}"
        
        # Decorative top border
        draw.rectangle([(0, 0), (w, 20)], fill=(0, 51, 102))
        draw.rectangle([(0, 20), (w, 28)], fill=(220, 180, 0))
        
        # School Logo/Emblem (circular)
        logo_x, logo_y = 200, 140
        draw.ellipse([(logo_x-70, logo_y-70), (logo_x+70, logo_y+70)], outline=(0, 51, 102), width=8)
        draw.ellipse([(logo_x-60, logo_y-60), (logo_x+60, logo_y+60)], outline=(220, 180, 0), width=4)
        draw.text((logo_x, logo_y), school["name"][0], fill=(0, 51, 102), font=font_logo, anchor="mm")
        
        # School Header
        y = 100
        draw.text((w//2, y), school["name"].upper(), fill=(0, 51, 102), font=font_title, anchor="mm")
        y += 70
        draw.rectangle([(w//2 - 500, y-5), (w//2 + 500, y+5)], fill=(220, 180, 0))
        y += 50
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 48
        draw.text((w//2, y), f"{school['town']}, {school['postcode']}", fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 48
        draw.text((w//2, y), f"Tel: {school.get('phone', '0800 000 0000')}", fill=(80, 80, 80), font=font_tiny, anchor="mm")
        
        # Reference and Date section
        y += 120
        draw.text((200, y), f"Ref: {ref_number}", fill=(0, 51, 102), font=font_bold)
        draw.text((w-200, y), current_date, fill=(80, 80, 80), font=font_normal, anchor="ra")
        
        # Recipient
        y += 140
        draw.text((200, y), "To Whom It May Concern", fill=(0, 0, 0), font=font_bold)
        
        # Subject line with background
        y += 130
        draw.rectangle([(180, y-15), (w-180, y+65)], fill=(245, 248, 255))
        draw.rectangle([(180, y-15), (200, y+65)], fill=(0, 51, 102))
        draw.text((220, y+25), "CONFIRMATION OF EMPLOYMENT", fill=(0, 51, 102), font=font_header, anchor="lm")
        
        # Body
        y += 140
        employment_year = random.randint(2015, 2022)
        body_paragraphs = [
            [
                f"This letter serves to confirm that {first} {last} is currently employed",
                f"at {school['name']} in the capacity of {position}.",
            ],
            [
                f"{first} {last} commenced employment with our institution in {employment_year}",
                f"and continues to serve on a full-time, permanent basis.",
            ],
            [
                f"Our institution is registered with {school.get('lea', school['town'] + ' Local Education')} ",
                f"Authority under Data Controller Number {data_controller}.",
            ],
        ]
        
        for paragraph in body_paragraphs:
            for line in paragraph:
                draw.text((200, y), line, fill=(40, 40, 40), font=font_normal)
                y += 58
            y += 30
        
        # Closing
        y += 50
        draw.text((200, y), "Yours faithfully,", fill=(40, 40, 40), font=font_normal)
        
        # Official stamp
        y += 100
        seal_x = 220
        seal_y = y + 60
        draw.ellipse([(seal_x-50, seal_y-50), (seal_x+50, seal_y+50)], outline=(180, 0, 0), width=4)
        draw.text((seal_x, seal_y), "OFFICIAL", fill=(180, 0, 0), font=font_tiny, anchor="mm")
        
        # Convert to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teacher_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Teacher ID Card"""
        w, h = 1280, 800
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        font_school = load_font('arialbd', 42)
        font_title = load_font('arialbd', 28)
        font_name = load_font('arialbd', 38)
        font_label = load_font('arial', 22)
        font_value = load_font('arialbd', 26)
        font_small = load_font('arial', 18)
        
        staff_id = f"STF-{random.randint(2020, 2025)}-{random.randint(100000, 999999)}"
        issue_date = datetime.now().strftime("%d/%m/%Y")
        
        primary_color = (0, 51, 102)
        secondary_color = (220, 180, 0)
        
        # Border
        draw.rectangle([(0, 0), (w-1, h-1)], outline=primary_color, width=8)
        draw.rectangle([(8, 8), (w-9, h-9)], outline=secondary_color, width=3)
        
        # Header
        draw.rectangle([(0, 0), (w, 140)], fill=primary_color)
        draw.text((w//2, 45), school["name"].upper(), fill=(255, 255, 255), font=font_school, anchor="mm")
        draw.text((w//2, 100), "TEACHING STAFF IDENTIFICATION", fill=secondary_color, font=font_title, anchor="mm")
        
        # Photo with border
        photo_size = (280, 340)
        photo_x, photo_y = 60, 180
        
        # Try to get real photo from foto folder
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            # Fallback to initials avatar
            photo = generate_initials_avatar(first, last, photo_size)
        
        img.paste(photo, (photo_x, photo_y))
        draw.rectangle([(photo_x-3, photo_y-3), (photo_x+photo_size[0]+3, photo_y+photo_size[1]+3)], 
                      outline=primary_color, width=5)
        
        # Information
        info_x = 380
        y = 200
        
        draw.text((info_x, y), "NAME", fill=(100, 100, 100), font=font_label)
        y += 35
        draw.text((info_x, y), f"{first.upper()} {last.upper()}", fill=primary_color, font=font_name)
        y += 70
        
        draw.text((info_x, y), "POSITION", fill=(100, 100, 100), font=font_label)
        y += 35
        draw.text((info_x, y), position[:30].upper(), fill=(0, 0, 0), font=font_value)
        y += 70
        
        draw.text((info_x, y), "STAFF ID", fill=(100, 100, 100), font=font_label)
        y += 35
        draw.text((info_x, y), staff_id, fill=(0, 0, 0), font=font_value)
        y += 70
        
        draw.text((info_x, y), "DATE OF BIRTH", fill=(100, 100, 100), font=font_label)
        y += 35
        draw.text((info_x, y), dob, fill=(0, 0, 0), font=font_value)
        
        # Right column
        info_x2 = 820
        y2 = 200
        
        draw.text((info_x2, y2), "ISSUE DATE", fill=(100, 100, 100), font=font_label)
        y2 += 35
        draw.text((info_x2, y2), issue_date, fill=(0, 0, 0), font=font_value)
        y2 += 140
        
        draw.text((info_x2, y2), "LEA", fill=(100, 100, 100), font=font_label)
        y2 += 35
        draw.text((info_x2, y2), school.get('lea', school['town'])[:20], fill=(0, 0, 0), font=font_value)
        
        # Bottom barcode
        bottom_y = 580
        draw.line([(30, bottom_y), (w-30, bottom_y)], fill=primary_color, width=3)
        
        barcode_y = bottom_y + 30
        for i in range(80):
            x = 60 + i * 13
            if random.random() > 0.3:
                draw.rectangle([(x, barcode_y), (x+random.choice([3,4,5,6]), barcode_y+80)], fill=(0, 0, 0))
        
        y = bottom_y + 130
        draw.text((w//2, y), f"Property of {school['name']}. Return if found.",
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_license(self, first: str, last: str) -> bytes:
        """Generate Teaching License (QTS Certificate)"""
        w, h = 3508, 2480  # A4 landscape
        img = Image.new('RGB', (w, h), (252, 250, 245))
        draw = ImageDraw.Draw(img)
        
        font_title = load_font('arialbd', 80)
        font_header = load_font('arialbd', 56)
        font_normal = load_font('arial', 42)
        font_bold = load_font('arialbd', 42)
        font_small = load_font('arial', 32)
        
        # Decorative border
        draw.rectangle([(60, 60), (w-60, h-60)], outline=(139, 0, 0), width=15)
        draw.rectangle([(80, 80), (w-80, h-80)], outline=(184, 134, 11), width=8)
        draw.rectangle([(95, 95), (w-95, h-95)], outline=(139, 0, 0), width=3)
        
        # UK Government coat of arms placeholder
        crest_y = 200
        draw.ellipse([(w//2-100, crest_y-100), (w//2+100, crest_y+100)], outline=(139, 0, 0), width=8)
        draw.text((w//2, crest_y), "DfE", fill=(139, 0, 0), font=font_title, anchor="mm")
        
        # Title
        y = crest_y + 180
        draw.text((w//2, y), "QUALIFIED TEACHER STATUS", fill=(139, 0, 0), font=font_title, anchor="mm")
        y += 100
        draw.text((w//2, y), "Department for Education", fill=(100, 100, 100), font=font_header, anchor="mm")
        
        # Certificate text
        y += 150
        draw.text((w//2, y), "This is to certify that", fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w//2, y), f"{first} {last}", fill=(0, 0, 0), font=font_header, anchor="mm")
        
        y += 120
        qts_number = f"QTS/{random.randint(10, 99)}/{random.randint(100000, 999999)}"
        lines = [
            f"has been awarded Qualified Teacher Status",
            f"in accordance with the Education Act 2002",
            f"and is registered with the Teaching Regulation Agency",
            f"",
            f"QTS Number: {qts_number}",
            f"Date of Award: {datetime.now().strftime('%d %B %Y')}",
        ]
        
        for line in lines:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 70
        
        # Signature section
        y += 100
        sig_y = y
        draw.line([(w//2 - 400, sig_y), (w//2 - 50, sig_y)], fill=(0, 0, 139), width=3)
        draw.line([(w//2 + 50, sig_y), (w//2 + 400, sig_y)], fill=(0, 0, 139), width=3)
        
        y += 40
        draw.text((w//2 - 225, y), "Chief Executive", fill=(80, 80, 80), font=font_small, anchor="mm")
        draw.text((w//2 + 225, y), "Date of Issue", fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 45
        draw.text((w//2 - 225, y), "Teaching Regulation Agency", fill=(100, 100, 100), font=font_small, anchor="mm")
        draw.text((w//2 + 225, y), datetime.now().strftime("%d/%m/%Y"), fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Official seal
        seal_x, seal_y = w - 350, h - 350
        draw.ellipse([(seal_x-120, seal_y-120), (seal_x+120, seal_y+120)], outline=(139, 0, 0), width=10)
        draw.ellipse([(seal_x-100, seal_y-100), (seal_x+100, seal_y+100)], outline=(184, 134, 11), width=5)
        draw.text((seal_x, seal_y-30), "OFFICIAL", fill=(139, 0, 0), font=font_bold, anchor="mm")
        draw.text((seal_x, seal_y+30), "SEAL", fill=(139, 0, 0), font=font_bold, anchor="mm")
        
        # Footer
        draw.text((w//2, h-150), "Department for Education, Teaching Regulation Agency", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        draw.text((w//2, h-100), f"Certificate Reference: {qts_number}", 
                 fill=(150, 150, 150), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
