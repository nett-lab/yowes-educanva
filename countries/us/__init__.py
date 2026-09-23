"""
US (United States) data and document generators
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar, load_font
from PIL import Image, ImageDraw
from datetime import datetime
import random


# US Schools Database (real org data researched per school)
DEFAULT_US_SCHOOLS = [
    {"name": "University Gardens (Especializada)", "address": "", "town": "San Juan", "postcode": "", "state": "PR", "phone": "(000) 000-0000", "lea": "University Gardens"},
    {"name": "IDEA University Prep", "address": "", "town": "Baton Rouge", "postcode": "", "state": "LA", "phone": "(000) 000-0000", "lea": "IDEA Public Schools"},
    {"name": "East Allen University", "address": "6501 Wayne Trace", "town": "Fort Wayne", "postcode": "46816", "state": "IN", "phone": "(260) 446-0240", "lea": "East Allen County Schools"},
    {"name": "Valley High", "address": "10200 Dixie Highway", "town": "Louisville", "postcode": "40272", "state": "KY", "phone": "(502) 485-8339", "lea": "Jefferson County"},
    {"name": "Norton Elementary", "address": "8101 Brownsboro Road", "town": "Louisville", "postcode": "40241", "state": "KY", "phone": "(502) 485-8308", "lea": "Jefferson County"},
    {"name": "Conway Middle", "address": "6300 Terry Road", "town": "Louisville", "postcode": "40258", "state": "KY", "phone": "(502) 485-8233", "lea": "Jefferson County"},
    {"name": "Field Elementary", "address": "120 Sacred Heart Lane", "town": "Louisville", "postcode": "40206", "state": "KY", "phone": "(502) 485-8252", "lea": "Jefferson County"},
    {"name": "King Elementary", "address": "4325 Vermont Avenue", "town": "Louisville", "postcode": "40211", "state": "KY", "phone": "(502) 485-8285", "lea": "Jefferson County"},
    {"name": "Liberty High", "address": "3901 Atkinson Square Drive", "town": "Louisville", "postcode": "40218", "state": "KY", "phone": "(502) 485-7100", "lea": "Jefferson County"},
    {"name": "Jefferson County Middle School", "address": "3232 State Hwy 296", "town": "Stapleton", "postcode": "30823", "state": "GA", "phone": "(478) 625-7764", "lea": "Jefferson County School District"},
    {"name": "Indian Trail Elementary", "address": "3709 East Indian Trail", "town": "Louisville", "postcode": "40213", "state": "KY", "phone": "(502) 485-8268", "lea": "Jefferson County"},
    {"name": "Mill Creek Elementary", "address": "3816 Dixie Highway", "town": "Louisville", "postcode": "40216", "state": "KY", "phone": "(502) 485-8301", "lea": "Jefferson County"},
    {"name": "Jefferson High School", "address": "4141 Flowing Springs Road", "town": "Shenandoah Junction", "postcode": "25442", "state": "WV", "phone": "(304) 725-8491", "lea": "Jefferson County Schools"},
    {"name": "Southern High", "address": "8620 Preston Highway", "town": "Louisville", "postcode": "40219", "state": "KY", "phone": "(502) 485-8330", "lea": "Jefferson County"},
    {"name": "Hawthorne Elementary", "address": "2301 Clarendon Avenue", "town": "Louisville", "postcode": "40205", "state": "KY", "phone": "(502) 485-8263", "lea": "Jefferson County"},
    {"name": "Bates Elementary", "address": "7601 Bardstown Road", "town": "Louisville", "postcode": "40291", "state": "KY", "phone": "(502) 485-8208", "lea": "Jefferson County"},
    {"name": "Wellington Elementary", "address": "4800 Kaufman Lane", "town": "Louisville", "postcode": "40216", "state": "KY", "phone": "(502) 485-8343", "lea": "Jefferson County"},
    {"name": "Auburndale Elementary", "address": "5749 New Cut Road", "town": "Louisville", "postcode": "40214", "state": "KY", "phone": "(502) 485-8204", "lea": "Jefferson County"},
    {"name": "Jackson Elementary School", "address": "1325 Mount Paran Road NW", "town": "Atlanta", "postcode": "30327", "state": "GA", "phone": "(404) 802-8800", "lea": "Atlanta Public Schools"},
    {"name": "Jackson Elementary School", "address": "620 South 31st Street", "town": "Omaha", "postcode": "68105", "state": "NE", "phone": "(531) 299-1620", "lea": "Omaha Public Schools"},
    {"name": "Jackson Elementary", "address": "", "town": "Ponca", "postcode": "", "state": "", "phone": "(000) 000-0000", "lea": "Ponca Public Schools"},
    {"name": "Jackson Middle", "address": "3020 Gallows Road", "town": "Falls Church", "postcode": "22042", "state": "VA", "phone": "(703) 204-8100", "lea": "Fairfax County Public Schools"},
    {"name": "Boyd Elementary School", "address": "4531 Broadmeadow Street", "town": "Jackson", "postcode": "39206", "state": "MS", "phone": "(601) 987-3504", "lea": "Jackson Public School District"},
]

# US Names
US_FIRST_NAMES = [
    "James", "Michael", "Robert", "John", "David", "William", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Karen", "Sarah",
    "Lisa", "Nancy", "Betty", "Sandra", "Margaret", "Ashley", "Kimberly", "Emily",
    "Amanda", "Melissa", "Rebecca", "Laura", "Angela", "Heather", "Nicole", "Megan"
]

US_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
]

# US Teaching Positions
US_TEACHING_POSITIONS = [
    "Head of English Department",
    "Head of Mathematics Department",
    "Head of Science Department",
    "Head of History Department",
    "Head of Social Studies Department",
    "Head of Modern Languages",
    "Head of Art Department",
    "Head of Music Department",
    "Head of PE Department",
    "Assistant Principal",
    "Dean of Students",
    "Instructional Coordinator",
    "Classroom Teacher - English",
    "Classroom Teacher - Mathematics",
    "Grade Level Lead Teacher",
]


class USGenerator(CountryGenerator):
    """US-specific document generator"""

    def get_country_name(self) -> str:
        return "United States"

    def get_country_code(self) -> str:
        return "us"

    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_US_SCHOOLS

    def get_first_names(self) -> List[str]:
        return US_FIRST_NAMES

    def get_last_names(self) -> List[str]:
        return US_LAST_NAMES

    def get_positions(self) -> List[str]:
        return US_TEACHING_POSITIONS

    def get_document_types(self) -> List[str]:
        return ["employment_letter", "teacher_id", "teaching_license"]

    def generate_document(self, doc_type: str, first: str, last: str,
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate US document"""
        if doc_type == "employment_letter":
            return self._generate_employment_letter(first, last, school, position)
        elif doc_type == "teacher_id":
            return self._generate_teacher_id(first, last, school, position, dob)
        elif doc_type == "teaching_license":
            return self._generate_teaching_license(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")

    def _school_location(self, school: Dict) -> str:
        """Format school location (town, state zip)"""
        state = school.get('state', '')
        postcode = school.get('postcode', '')
        parts = [school.get('town', '')]
        if state:
            parts.append(state)
        if postcode:
            parts.append(postcode)
        return ", ".join(p for p in parts if p)

    def _generate_employment_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Employment Verification Letter (US format)"""
        w, h = 2480, 3508  # A4 at 300 DPI
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        from ..utils import load_font

        font_logo = load_font('arialbd', 68)
        font_title = load_font('arialbd', 50)
        font_header = load_font('arialbd', 42)
        font_normal = load_font('arial', 35)
        font_bold = load_font('arialbd', 35)
        font_small = load_font('arial', 30)
        font_tiny = load_font('arial', 26)

        current_date = datetime.now().strftime("%B %d, %Y")
        ref_number = f"VER/{random.randint(1000, 9999)}/{datetime.now().year}"

        # Decorative top border
        draw.rectangle([(0, 0), (w, 20)], fill=(20, 60, 130))
        draw.rectangle([(0, 20), (w, 28)], fill=(200, 60, 60))

        # School Logo/Emblem (circular)
        logo_x, logo_y = 200, 140
        draw.ellipse([(logo_x-70, logo_y-70), (logo_x+70, logo_y+70)], outline=(20, 60, 130), width=8)
        draw.ellipse([(logo_x-60, logo_y-60), (logo_x+60, logo_y+60)], outline=(200, 60, 60), width=4)
        draw.text((logo_x, logo_y), school["name"][0], fill=(20, 60, 130), font=font_logo, anchor="mm")

        # School Header
        y = 100
        draw.text((w//2, y), school["name"].upper(), fill=(20, 60, 130), font=font_title, anchor="mm")
        y += 70
        draw.rectangle([(w//2 - 500, y-5), (w//2 + 500, y+5)], fill=(200, 60, 60))
        y += 50
        draw.text((w//2, y), school.get("address", ""), fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 48
        draw.text((w//2, y), self._school_location(school), fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 48
        draw.text((w//2, y), f"Tel: {school.get('phone', '(000) 555-0000')}", fill=(80, 80, 80), font=font_tiny, anchor="mm")

        # Reference and Date section
        y += 120
        draw.text((200, y), f"Ref: {ref_number}", fill=(20, 60, 130), font=font_bold)
        draw.text((w-200, y), current_date, fill=(80, 80, 80), font=font_normal, anchor="ra")

        # Recipient
        y += 140
        draw.text((200, y), "TO WHOM IT MAY CONCERN", fill=(0, 0, 0), font=font_bold)

        # Subject line with background
        y += 130
        draw.rectangle([(180, y-15), (w-180, y+65)], fill=(240, 245, 255))
        draw.rectangle([(180, y-15), (200, y+65)], fill=(20, 60, 130))
        draw.text((220, y+25), "VERIFICATION OF EMPLOYMENT", fill=(20, 60, 130), font=font_header, anchor="lm")

        # Body
        y += 140
        employment_year = random.randint(2015, 2022)
        body_paragraphs = [
            [
                f"This letter certifies that {first} {last} is currently employed",
                f"at {school['name']} in the capacity of {position}.",
            ],
            [
                f"{first} {last} began employment with our institution in {employment_year}",
                f"and serves on a full-time, permanent basis.",
            ],
            [
                f"Our school is accredited under {school.get('lea', school['town'] + ' Public Schools')}",
                f"and licensed by the {school.get('state', 'State')} Department of Education.",
            ],
        ]

        for paragraph in body_paragraphs:
            for line in paragraph:
                draw.text((200, y), line, fill=(40, 40, 40), font=font_normal)
                y += 58
            y += 30

        # Closing
        y += 50
        draw.text((200, y), "Sincerely,", fill=(40, 40, 40), font=font_normal)

        # Official stamp
        y += 100
        seal_x = 220
        seal_y = y + 60
        draw.ellipse([(seal_x-50, seal_y-50), (seal_x+50, seal_y+50)], outline=(180, 0, 0), width=4)
        draw.text((seal_x, seal_y), "OFFICIAL", fill=(180, 0, 0), font=font_tiny, anchor="mm")

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

        staff_id = f"EMP-{random.randint(2020, 2025)}-{random.randint(100000, 999999)}"
        issue_date = datetime.now().strftime("%m/%d/%Y")

        primary_color = (20, 60, 130)
        secondary_color = (200, 60, 60)

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

        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
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

        draw.text((info_x, y), "EMPLOYEE ID", fill=(100, 100, 100), font=font_label)
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

        draw.text((info_x2, y2), "DISTRICT", fill=(100, 100, 100), font=font_label)
        y2 += 35
        draw.text((info_x2, y2), school.get('lea', school['town'])[:22], fill=(0, 0, 0), font=font_value)

        # Bottom barcode
        bottom_y = 580
        draw.line([(30, bottom_y), (w-30, bottom_y)], fill=primary_color, width=3)

        barcode_y = bottom_y + 30
        for i in range(80):
            x = 60 + i * 13
            if random.random() > 0.3:
                draw.rectangle([(x, barcode_y), (x+random.choice([3, 4, 5, 6]), barcode_y+80)], fill=(0, 0, 0))

        y = bottom_y + 130
        draw.text((w//2, y), f"Property of {school['name']}. Return if found.",
                 fill=(120, 120, 120), font=font_small, anchor="mm")

        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def _generate_teaching_license(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Teaching License (State Credential)"""
        w, h = 3508, 2480  # A4 landscape
        img = Image.new('RGB', (w, h), (250, 248, 245))
        draw = ImageDraw.Draw(img)

        font_title = load_font('arialbd', 72)
        font_header = load_font('arialbd', 52)
        font_normal = load_font('arial', 42)
        font_bold = load_font('arialbd', 42)
        font_small = load_font('arial', 32)

        state = school.get('state', 'State')
        license_number = f"TCH-{random.randint(100000, 999999)}-{state}"

        # Decorative border
        draw.rectangle([(60, 60), (w-60, h-60)], outline=(20, 60, 130), width=15)
        draw.rectangle([(80, 80), (w-80, h-80)], outline=(200, 60, 60), width=8)
        draw.rectangle([(95, 95), (w-95, h-95)], outline=(20, 60, 130), width=3)

        # State seal placeholder
        crest_y = 200
        draw.ellipse([(w//2-100, crest_y-100), (w//2+100, crest_y+100)], outline=(20, 60, 130), width=8)
        draw.text((w//2, crest_y), state, fill=(20, 60, 130), font=font_title, anchor="mm")

        # Title
        y = crest_y + 180
        draw.text((w//2, y), "TEACHING LICENSE", fill=(20, 60, 130), font=font_title, anchor="mm")
        y += 100
        draw.text((w//2, y), f"{state} Department of Education", fill=(100, 100, 100), font=font_header, anchor="mm")

        # Certificate text
        y += 150
        draw.text((w//2, y), "This certifies that", fill=(80, 80, 80), font=font_normal, anchor="mm")

        y += 100
        draw.text((w//2, y), f"{first} {last}", fill=(0, 0, 0), font=font_header, anchor="mm")

        y += 120
        lines = [
            f"has been licensed to teach in the state of {state}",
            f"for the position of {position}",
            f"and is registered with the {state} Board of Education",
            f"",
            f"License Number: {license_number}",
            f"Date of Issue: {datetime.now().strftime('%B %d, %Y')}",
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
        draw.text((w//2 - 225, y), "Superintendent", fill=(80, 80, 80), font=font_small, anchor="mm")
        draw.text((w//2 + 225, y), "Date of Issue", fill=(80, 80, 80), font=font_small, anchor="mm")
        y += 45
        draw.text((w//2 - 225, y), f"{state} Department of Education", fill=(100, 100, 100), font=font_small, anchor="mm")
        draw.text((w//2 + 225, y), datetime.now().strftime("%m/%d/%Y"), fill=(100, 100, 100), font=font_small, anchor="mm")

        # Official seal
        seal_x, seal_y = w - 350, h - 350
        draw.ellipse([(seal_x-120, seal_y-120), (seal_x+120, seal_y+120)], outline=(20, 60, 130), width=10)
        draw.ellipse([(seal_x-100, seal_y-100), (seal_x+100, seal_y+100)], outline=(200, 60, 60), width=5)
        draw.text((seal_x, seal_y-30), "OFFICIAL", fill=(20, 60, 130), font=font_bold, anchor="mm")
        draw.text((seal_x, seal_y+30), "SEAL", fill=(20, 60, 130), font=font_bold, anchor="mm")

        # Footer
        draw.text((w//2, h-150), f"{state} Department of Education, Office of Certification",
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        draw.text((w//2, h-100), f"License Reference: {license_number}",
                 fill=(150, 150, 150), font=font_small, anchor="mm")

        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
