"""
Thailand data and document generators

Thai teacher verification requirements:
1. Teacher License Card (ใบอนุญาตประกอบวิชาชีพครู)
2. Employment Certificate (หนังสือรับรองการทำงาน)
3. School ID Card (บัตรประจำตัวครู)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Thailand Universities Database
DEFAULT_THAILAND_SCHOOLS = [
    {"name": "Bangkok Patana School", "address": "643 Lasalle Road, Bangna", "city": "Bangkok", "region": "Bangkok", "postcode": "10260", "phone": "+66 2 785 2200", "domain": "patana.ac.th"},
    {"name": "International School Bangkok", "address": "39/7 Soi Nichada Thani, Pakkret", "city": "Nonthaburi", "region": "Central Thailand", "postcode": "11120", "phone": "+66 2 963 5800", "domain": "isb.ac.th"},
    {"name": "NIST International School", "address": "36 Sukhumvit 15, Wattana", "city": "Bangkok", "region": "Bangkok", "postcode": "10110", "phone": "+66 2 651 2065", "domain": "nist.ac.th"},
    {"name": "Triam Udom Suksa School", "address": "227 Phaya Thai Road, Pathum Wan", "city": "Bangkok", "region": "Bangkok", "postcode": "10330", "phone": "+66 2 254 0287", "domain": "triamudom.ac.th"},
    {"name": "Suankularb Wittayalai School", "address": "88 Tri Phet Road, Phra Nakhon", "city": "Bangkok", "region": "Bangkok", "postcode": "10200", "phone": "+66 2 221 0843", "domain": "sk.ac.th"},
    {"name": "Bangkok Christian College", "address": "35 Pramuan Road, Bang Rak", "city": "Bangkok", "region": "Bangkok", "postcode": "10500", "phone": "+66 2 637 1852", "domain": "bcc.ac.th"},
    {"name": "Mater Dei School", "address": "534 Phloen Chit Road, Pathum Wan", "city": "Bangkok", "region": "Bangkok", "postcode": "10330", "phone": "+66 2 252 6316", "domain": "materdei.ac.th"},
    {"name": "Saint Joseph Convent School", "address": "7 Convent Road, Silom, Bang Rak", "city": "Bangkok", "region": "Bangkok", "postcode": "10500", "phone": "+66 2 234 0561", "domain": "sjc.ac.th"},
    {"name": "Assumption College", "address": "26 Soi Charoen Krung 40, Bang Rak", "city": "Bangkok", "region": "Bangkok", "postcode": "10500", "phone": "+66 2 630 7111", "domain": "assumption.ac.th"},
    {"name": "Ruamrudee International School", "address": "6 Ramkhamhaeng 184, Min Buri", "city": "Bangkok", "region": "Bangkok", "postcode": "10510", "phone": "+66 2 791 8900", "domain": "rism.ac.th"},
    {"name": "Harrow International School Bangkok", "address": "45 Soi Kosumruamchai 14, Don Mueang", "city": "Bangkok", "region": "Bangkok", "postcode": "10210", "phone": "+66 2 503 7222", "domain": "harrowschool.ac.th"},
    {"name": "Shrewsbury International School", "address": "1922 Charoen Krung Road, Wat Phraya Krai", "city": "Bangkok", "region": "Bangkok", "postcode": "10120", "phone": "+66 2 675 1888", "domain": "shrewsbury.ac.th"},
    {"name": "Prem Tinsulanonda International School", "address": "234 Moo 3, Huay Sai, Mae Rim", "city": "Chiang Mai", "region": "Northern Thailand", "postcode": "50180", "phone": "+66 53 301 500", "domain": "ptis.ac.th"},
    {"name": "Chiang Mai International School", "address": "13 Chetupon Road, Wat Ket", "city": "Chiang Mai", "region": "Northern Thailand", "postcode": "50000", "phone": "+66 53 306 152", "domain": "cmis.ac.th"},
    {"name": "Hatyai Wittayalai School", "address": "467 Phetkasem Road", "city": "Hat Yai, Songkhla", "region": "Southern Thailand", "postcode": "90110", "phone": "+66 74 261 778", "domain": "hatyaiwit.ac.th"},
]

# Thai Names
THAILAND_FIRST_NAMES = [
    "Somchai", "Somsak", "Nattawut", "Apinya", "Siriporn", "Rattana", "Watchara", "Narong",
    "Pornthip", "Wanida", "Suphatra", "Chanida", "Pattara", "Anong", "Suthep", "Kamol",
    "Preecha", "Prasert", "Wichit", "Montri", "Thida", "Siriwan", "Porn", "Chaiwat",
    "Somjai", "Niran", "Chalerm", "Anan", "Boonmee", "Charoen", "Manit", "Sakchai"
]

THAILAND_LAST_NAMES = [
    "Srisuwan", "Rattanasombat", "Chanthavong", "Phongphanit", "Suksawat", "Kittikhun", "Wongsawat", "Charoenpol",
    "Prachakul", "Namsomboon", "Thongchai", "Siripanich", "Boonlert", "Rattanakorn", "Phakdeewong", "Tantiwong",
    "Intharaprasert", "Wongcharoen", "Siriratana", "Pattanakul", "Thanaporn", "Kittisak", "Wongsawang", "Prasertpong",
    "Jantarasombat", "Bunditsakul", "Sukkasem", "Chaiyaporn", "Ratchataporn", "Sawatdee", "Mongkol", "Thepsiri"
]

# Thai K-12 Teaching Positions (Anuban, Prathom, Mathayom)
THAILAND_TEACHING_POSITIONS = [
    "ครูอนุบาล (Kindergarten Teacher)",
    "ครูประถม (Primary School Teacher)",
    "ครูประจำชั้น (Homeroom Teacher)",
    "ครูผู้ช่วย (Assistant Teacher)",
    "ครู ค.ศ.1 (Teacher Level 1)",
    "ครู ค.ศ.2 (Teacher Level 2)",
    "ครูชำนาญการ (Senior Teacher)",
    "ครูชำนาญการพิเศษ (Expert Teacher)",
    "ครูภาษาอังกฤษ (English Teacher)",
    "ครูคณิตศาสตร์ (Mathematics Teacher)",
    "ครูวิทยาศาสตร์ (Science Teacher)",
    "ครูสังคมศึกษา (Social Studies Teacher)",
    "ครูภาษาไทย (Thai Language Teacher)",
    "ครูพลศึกษา (Physical Education Teacher)",
    "ครูศิลปะ (Art Teacher)",
    "ครูดนตรี (Music Teacher)",
    "ครูคอมพิวเตอร์ (Computer Teacher)",
    "ครูแนะแนว (Guidance Counselor)",
    "หัวหน้ากลุ่มสาระ (Subject Group Head)",
    "รองผู้อำนวยการฝ่ายวิชาการ (Vice Principal - Academic)",
]


class ThailandGenerator(CountryGenerator):
    """Thailand-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Thailand"
    
    def get_country_code(self) -> str:
        return "thailand"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_THAILAND_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return THAILAND_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return THAILAND_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return THAILAND_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["payslip", "letter_of_employment"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Thailand document"""
        if doc_type == "payslip":
            return self._generate_payslip(first, last, school, position, dob)
        elif doc_type == "letter_of_employment":
            return self._generate_letter_of_employment(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_teacher_license(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Thai Teacher License Card"""
        # Create image 1000x630 pixels
        img = Image.new('RGB', (1000, 630), color='white')
        draw = ImageDraw.Draw(img)
        
        # Colors - Thai flag colors
        header_color = (45, 50, 130)  # Navy blue (from Thai flag)
        red_color = (237, 28, 36)  # Red (from Thai flag)
        text_color = (0, 0, 0)
        
        # Draw header with Thai colors
        draw.rectangle([0, 0, 1000, 15], fill=red_color)
        draw.rectangle([0, 15, 1000, 130], fill=header_color)
        
        # Title - bilingual
        title_font = load_font(36, bold=True)
        subtitle_font = load_font(20)
        draw.text((500, 50), "ใบอนุญาตประกอบวิชาชีพครู", font=title_font, fill='white', anchor='mm')
        draw.text((500, 90), "TEACHER'S LICENSE", font=subtitle_font, fill='white', anchor='mm')
        draw.text((500, 110), "Teachers' Council of Thailand", font=subtitle_font, fill='white', anchor='mm')
        
        # Red stripe
        draw.rectangle([0, 130, 1000, 145], fill=red_color)
        
        # Photo placeholder
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(person_id=person_id, gender=gender)
        if photo:
            photo = photo.resize((200, 240))
            img.paste(photo, (50, 180))
        else:
            draw.rectangle([50, 180, 250, 420], fill=(200, 200, 200))
            avatar = generate_initials_avatar(first, last, size=200)
            img.paste(avatar, (50, 180))
        
        # Information
        info_font = load_font(22, bold=True)
        value_font = load_font(20)
        
        y_pos = 190
        spacing = 48
        
        # License Number
        license_no = f"TH-{random.randint(100000, 999999)}"
        draw.text((280, y_pos), "LICENSE NO:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), license_no, font=value_font, fill=red_color)
        
        y_pos += spacing
        
        # Name
        draw.text((280, y_pos), "NAME:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), f"{first} {last}", font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Date of Birth
        draw.text((280, y_pos), "DATE OF BIRTH:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), dob, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Position
        draw.text((280, y_pos), "POSITION:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), position, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Issue Date
        issue_date = datetime.now().strftime("%d/%m/%Y")
        draw.text((280, y_pos), "ISSUE DATE:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), issue_date, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Expiry Date
        expiry_year = datetime.now().year + 5
        draw.text((280, y_pos), "EXPIRY DATE:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 24), f"31/12/{expiry_year}", font=value_font, fill=text_color)
        
        # Signature area
        draw.line([50, 480, 250, 480], fill=text_color, width=2)
        sig_font = load_font(14)
        draw.text((150, 490), "License Holder", font=sig_font, fill=text_color, anchor='mm')
        
        # QR Code placeholder with pattern
        qr_size = 150
        qr_x, qr_y = 750, 180
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
        corner_size = 22
        for cx, cy in [(qr_x + 5, qr_y + 5), (qr_x + qr_size - corner_size - 5, qr_y + 5), (qr_x + 5, qr_y + qr_size - corner_size - 5)]:
            draw.rectangle([cx, cy, cx + corner_size, cy + corner_size], outline=text_color, width=2)
            draw.rectangle([cx + 7, cy + 7, cx + corner_size - 7, cy + corner_size - 7], fill=text_color)
        
        draw.text((825, 350), "Scan to verify", font=sig_font, fill=text_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 570), "คุรุสภา (Teachers' Council of Thailand)", font=footer_font, fill=text_color, anchor='mm')
        draw.text((500, 595), "This license is valid throughout the Kingdom of Thailand", 
                 font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_payslip(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Thai Payslip"""
        # Create image 1000x1400 pixels
        img = Image.new('RGB', (1000, 1400), color='white')
        draw = ImageDraw.Draw(img)
        
        text_color = (0, 0, 0)
        header_color = (45, 50, 130)
        accent_color = (237, 28, 36)
        
        # Header
        draw.rectangle([0, 0, 1000, 120], fill=header_color)
        
        header_font = load_font(36, bold=True)
        draw.text((500, 60), "PAYSLIP / ใบแจ้งเงินเดือน", font=header_font, fill='white', anchor='mm')
        
        # School info
        school_font = load_font(24, bold=True)
        info_font = load_font(18)
        
        draw.text((500, 180), school['name'], font=school_font, fill=text_color, anchor='mm')
        draw.text((500, 215), f"{school['address']}, {school['city']}", font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 245), f"Tel: {school['phone']}", font=info_font, fill=text_color, anchor='mm')
        
        # Draw line
        draw.line([50, 280, 950, 280], fill=accent_color, width=3)
        
        # Payslip details
        detail_font = load_font(20, bold=True)
        value_font = load_font(18)
        
        y_pos = 320
        
        # Pay period
        current_month = datetime.now().strftime("%B %Y")
        draw.text((50, y_pos), "PAY PERIOD:", font=detail_font, fill=text_color)
        draw.text((300, y_pos), current_month, font=value_font, fill=text_color)
        
        draw.text((550, y_pos), "PAYMENT DATE:", font=detail_font, fill=text_color)
        draw.text((800, y_pos), datetime.now().strftime("%d/%m/%Y"), font=value_font, fill=text_color)
        
        y_pos += 60
        
        # Employee details
        draw.text((50, y_pos), "EMPLOYEE NAME:", font=detail_font, fill=text_color)
        draw.text((300, y_pos), f"{first} {last}", font=value_font, fill=text_color)
        
        y_pos += 40
        
        draw.text((50, y_pos), "POSITION:", font=detail_font, fill=text_color)
        draw.text((300, y_pos), position, font=value_font, fill=text_color)
        
        y_pos += 40
        
        draw.text((50, y_pos), "EMPLOYEE ID:", font=detail_font, fill=text_color)
        emp_id = f"TH-{random.randint(10000, 99999)}"
        draw.text((300, y_pos), emp_id, font=value_font, fill=text_color)
        
        y_pos += 80
        
        # Earnings section
        draw.rectangle([50, y_pos, 950, y_pos + 40], fill=header_color)
        section_font = load_font(22, bold=True)
        draw.text((500, y_pos + 20), "EARNINGS / รายได้", font=section_font, fill='white', anchor='mm')
        
        y_pos += 60
        
        # Salary breakdown
        base_salary = random.randint(35000, 65000)
        allowance = random.randint(3000, 8000)
        total_earnings = base_salary + allowance
        
        draw.text((100, y_pos), "Basic Salary:", font=value_font, fill=text_color)
        draw.text((850, y_pos), f"{base_salary:,} THB", font=value_font, fill=text_color, anchor='rm')
        
        y_pos += 35
        
        draw.text((100, y_pos), "Allowance:", font=value_font, fill=text_color)
        draw.text((850, y_pos), f"{allowance:,} THB", font=value_font, fill=text_color, anchor='rm')
        
        y_pos += 35
        draw.line([100, y_pos, 850, y_pos], fill=text_color, width=1)
        y_pos += 10
        
        draw.text((100, y_pos), "TOTAL EARNINGS:", font=detail_font, fill=text_color)
        draw.text((850, y_pos), f"{total_earnings:,} THB", font=detail_font, fill=accent_color, anchor='rm')
        
        y_pos += 60
        
        # Deductions section
        draw.rectangle([50, y_pos, 950, y_pos + 40], fill=header_color)
        draw.text((500, y_pos + 20), "DEDUCTIONS / รายการหัก", font=section_font, fill='white', anchor='mm')
        
        y_pos += 60
        
        tax = int(total_earnings * 0.05)
        social_security = int(total_earnings * 0.05)
        total_deductions = tax + social_security
        
        draw.text((100, y_pos), "Income Tax:", font=value_font, fill=text_color)
        draw.text((850, y_pos), f"{tax:,} THB", font=value_font, fill=text_color, anchor='rm')
        
        y_pos += 35
        
        draw.text((100, y_pos), "Social Security:", font=value_font, fill=text_color)
        draw.text((850, y_pos), f"{social_security:,} THB", font=value_font, fill=text_color, anchor='rm')
        
        y_pos += 35
        draw.line([100, y_pos, 850, y_pos], fill=text_color, width=1)
        y_pos += 10
        
        draw.text((100, y_pos), "TOTAL DEDUCTIONS:", font=detail_font, fill=text_color)
        draw.text((850, y_pos), f"{total_deductions:,} THB", font=detail_font, fill=text_color, anchor='rm')
        
        y_pos += 60
        
        # Net pay
        net_pay = total_earnings - total_deductions
        draw.rectangle([50, y_pos, 950, y_pos + 60], fill=(240, 240, 240))
        net_font = load_font(26, bold=True)
        draw.text((100, y_pos + 30), "NET PAY:", font=net_font, fill=text_color)
        draw.text((850, y_pos + 30), f"{net_pay:,} THB", font=net_font, fill=accent_color, anchor='rm')
        
        y_pos += 100
        
        # Footer notes
        note_font = load_font(14)
        draw.text((50, y_pos), "Notes:", font=detail_font, fill=text_color)
        y_pos += 30
        draw.text((70, y_pos), "• This is a computer-generated payslip and does not require a signature.", font=note_font, fill=text_color)
        y_pos += 25
        draw.text((70, y_pos), "• Please keep this payslip for your records.", font=note_font, fill=text_color)
        y_pos += 25
        draw.text((70, y_pos), "• For any inquiries, please contact the HR department.", font=note_font, fill=text_color)
        
        # Bottom signature area
        y_pos += 80
        draw.line([100, y_pos, 400, y_pos], fill=text_color, width=2)
        draw.line([600, y_pos, 900, y_pos], fill=text_color, width=2)
        
        sig_font = load_font(16, bold=True)
        draw.text((250, y_pos + 20), "Prepared By", font=sig_font, fill=text_color, anchor='mm')
        draw.text((750, y_pos + 20), "Approved By", font=sig_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_letter_of_employment(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Letter of Employment"""
        # Create image 1000x1400 pixels
        img = Image.new('RGB', (1000, 1400), color='white')
        draw = ImageDraw.Draw(img)
        
        text_color = (0, 0, 0)
        header_color = (45, 50, 130)
        accent_color = (237, 28, 36)
        
        # Header with Thai colors
        draw.rectangle([0, 0, 1000, 10], fill=accent_color)
        draw.rectangle([0, 10, 1000, 150], fill=header_color)
        
        header_font = load_font(36, bold=True)
        draw.text((500, 60), "หนังสือรับรองการทำงาน", font=header_font, fill='white', anchor='mm')
        draw.text((500, 100), "EMPLOYMENT CERTIFICATE", font=header_font, fill='white', anchor='mm')
        
        # School letterhead
        school_font = load_font(26, bold=True)
        info_font = load_font(18)
        
        draw.text((500, 220), school['name'], font=school_font, fill=text_color, anchor='mm')
        draw.text((500, 260), f"{school['address']}", font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 290), f"{school['city']}, {school['region']}, Thailand", 
                 font=info_font, fill=text_color, anchor='mm')
        draw.text((500, 320), f"Tel: {school['phone']}", font=info_font, fill=text_color, anchor='mm')
        
        # Draw line
        draw.line([100, 360, 900, 360], fill=text_color, width=2)
        
        # Document number
        doc_no = f"EMP-{random.randint(1000, 9999)}/{datetime.now().year}"
        draw.text((500, 390), f"Document No: {doc_no}", font=info_font, fill=text_color, anchor='mm')
        
        # Date
        date_font = load_font(20)
        current_date = datetime.now().strftime("%B %d, %Y")
        draw.text((800, 440), current_date, font=date_font, fill=text_color, anchor='rm')
        
        # Letter title
        title_font = load_font(24, bold=True)
        draw.text((500, 500), "TO WHOM IT MAY CONCERN", font=title_font, fill=text_color, anchor='mm')
        
        # Letter body
        body_font = load_font(20)
        y_pos = 570
        line_spacing = 35
        
        lines = [
            f"This is to certify that Mr./Ms. {first} {last} has been",
            f"employed at {school['name']} as",
            f"{position} since {datetime.now().year - random.randint(1, 5)}.",
            "",
            "During his/her employment, he/she has:",
            "",
            "• Demonstrated excellent teaching skills and professionalism",
            "• Actively participated in curriculum development",
            "• Contributed to student academic achievement",
            "• Maintained good relationships with students and colleagues",
            "• Participated in professional development activities",
            "",
            "He/She is currently employed on a full-time basis and holds",
            "a valid teaching license from the Teachers' Council of Thailand.",
            "",
            "This certificate is issued for official purposes as requested",
            "by the employee.",
            "",
            "Should you require any additional information, please do not",
            "hesitate to contact us.",
        ]
        
        for line in lines:
            if line.startswith("•"):
                draw.text((120, y_pos), line, font=body_font, fill=text_color)
            else:
                draw.text((100, y_pos), line, font=body_font, fill=text_color)
            y_pos += line_spacing
        
        # Signatures
        y_pos += 50
        draw.text((500, y_pos), "Sincerely,", font=date_font, fill=text_color, anchor='mm')
        
        y_pos += 80
        draw.line([150, y_pos, 450, y_pos], fill=text_color, width=2)
        draw.line([550, y_pos, 850, y_pos], fill=text_color, width=2)
        
        sig_font = load_font(16, bold=True)
        draw.text((300, y_pos + 20), "Director/Principal", font=sig_font, fill=text_color, anchor='mm')
        draw.text((700, y_pos + 20), "HR Manager", font=sig_font, fill=text_color, anchor='mm')
        
        # Official seal placeholder
        draw.ellipse([400, y_pos - 100, 600, y_pos + 10], outline=accent_color, width=3)
        seal_font = load_font(16)
        draw.text((500, y_pos - 45), "OFFICIAL", font=seal_font, fill=accent_color, anchor='mm')
        draw.text((500, y_pos - 25), "SEAL", font=seal_font, fill=accent_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 1350), "This is an official document - Unauthorized use is prohibited", 
                 font=footer_font, fill=text_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_school_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate School ID Card"""
        # Create image 1000x630 pixels
        img = Image.new('RGB', (1000, 630), color='white')
        draw = ImageDraw.Draw(img)
        
        # Colors
        header_color = (45, 50, 130)
        accent_color = (237, 28, 36)
        text_color = (0, 0, 0)
        
        # Draw header
        draw.rectangle([0, 0, 1000, 130], fill=header_color)
        
        # Title
        title_font = load_font(32, bold=True)
        subtitle_font = load_font(18)
        draw.text((500, 40), "TEACHER IDENTIFICATION CARD", font=title_font, fill='white', anchor='mm')
        draw.text((500, 75), "บัตรประจำตัวครู", font=subtitle_font, fill='white', anchor='mm')
        draw.text((500, 100), school['name'], font=subtitle_font, fill='white', anchor='mm')
        
        # Accent stripe
        draw.rectangle([0, 130, 1000, 145], fill=accent_color)
        
        # Photo
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(person_id=person_id, gender=gender)
        if photo:
            photo = photo.resize((200, 240))
            img.paste(photo, (50, 180))
        else:
            draw.rectangle([50, 180, 250, 420], fill=(200, 200, 200))
            avatar = generate_initials_avatar(first, last, size=200)
            img.paste(avatar, (50, 180))
        
        # Card Information
        info_font = load_font(24, bold=True)
        value_font = load_font(22)
        
        y_pos = 190
        spacing = 50
        
        # Employee ID
        emp_id = f"EMP-{random.randint(10000, 99999)}"
        draw.text((280, y_pos), "EMPLOYEE ID:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 26), emp_id, font=value_font, fill=accent_color)
        
        y_pos += spacing
        
        # Name
        draw.text((280, y_pos), "NAME:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 26), f"{first} {last}", font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Position
        draw.text((280, y_pos), "POSITION:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 26), position, font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Department
        draw.text((280, y_pos), "DEPARTMENT:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 26), "Academic Faculty", font=value_font, fill=text_color)
        
        y_pos += spacing
        
        # Issue Date
        issue_date = datetime.now().strftime("%d/%m/%Y")
        draw.text((280, y_pos), "ISSUE DATE:", font=info_font, fill=text_color)
        draw.text((280, y_pos + 26), issue_date, font=value_font, fill=text_color)
        
        # Barcode placeholder with realistic pattern
        barcode_x, barcode_y = 650, 200
        barcode_width, barcode_height = 270, 80
        draw.rectangle([barcode_x, barcode_y, barcode_x + barcode_width, barcode_y + barcode_height], 
                      fill='white', outline=text_color, width=2)
        
        # Draw barcode-like vertical lines with varying widths
        x_offset = barcode_x + 10
        bar_heights = barcode_height - 20
        while x_offset < barcode_x + barcode_width - 10:
            bar_width = random.choice([2, 3, 4, 5, 6])
            if random.choice([True, False]):
                draw.rectangle([x_offset, barcode_y + 10, x_offset + bar_width, barcode_y + 10 + bar_heights],
                              fill=text_color)
            x_offset += bar_width + random.choice([2, 3])
        
        barcode_font = load_font(12)
        draw.text((785, 295), emp_id, font=barcode_font, fill=text_color, anchor='mm')
        
        # Signature
        draw.line([50, 480, 250, 480], fill=text_color, width=2)
        sig_font = load_font(14)
        draw.text((150, 490), "Cardholder Signature", font=sig_font, fill=text_color, anchor='mm')
        
        draw.line((700, 480, 900, 480), fill=text_color, width=2)
        draw.text((800, 490), "Authorized Signature", font=sig_font, fill=text_color, anchor='mm')
        
        # Footer
        footer_font = load_font(14)
        draw.text((500, 550), f"{school['address']}, {school['city']}", 
                 font=footer_font, fill=text_color, anchor='mm')
        draw.text((500, 575), f"Tel: {school['phone']} | {school['domain']}", 
                 font=footer_font, fill=text_color, anchor='mm')
        draw.text((500, 600), "If found, please return to the above address", 
                 font=footer_font, fill=accent_color, anchor='mm')
        
        # Save to bytes
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


# Create generator instance
generator = ThailandGenerator()
