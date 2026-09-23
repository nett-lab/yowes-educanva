"""
Indonesia data and document generators

Indonesian teacher verification requirements:
1. Payslip (Slip Gaji)
2. Teaching Experience Letter (Surat Keterangan Mengajar)
3. NUPTK Card (Kartu NUPTK)
4. Appointment Letter (SK Pengangkatan)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# Indonesia Schools Database
DEFAULT_INDONESIA_SCHOOLS = [
    {"name": "SMA Negeri 3 Jakarta", "address": "Jl. Setiabudi Tengah No. 1", "city": "Jakarta Selatan", "province": "DKI Jakarta", "postcode": "12910", "phone": "021-5209516", "npsn": "20100521", "domain": "sman3jakarta.sch.id"},
    {"name": "SMA Negeri 8 Jakarta", "address": "Jl. Taman Bukit Duri No. 1", "city": "Jakarta Selatan", "province": "DKI Jakarta", "postcode": "12840", "phone": "021-8292202", "npsn": "20100538", "domain": "sman8jakarta.sch.id"},
    {"name": "SMA Negeri 5 Surabaya", "address": "Jl. Kusuma Bangsa No. 21", "city": "Surabaya", "province": "Jawa Timur", "postcode": "60272", "phone": "031-5342094", "npsn": "20532619", "domain": "sman5surabaya.sch.id"},
    {"name": "SMA Negeri 1 Yogyakarta", "address": "Jl. HOS Cokroaminoto No. 10", "city": "Yogyakarta", "province": "DI Yogyakarta", "postcode": "55224", "phone": "0274-512375", "npsn": "20403280", "domain": "sman1yogyakarta.sch.id"},
    {"name": "SMA Negeri 3 Bandung", "address": "Jl. Belitung No. 8", "city": "Bandung", "province": "Jawa Barat", "postcode": "40261", "phone": "022-4231046", "npsn": "20219151", "domain": "sman3bandung.sch.id"},
    {"name": "SMA Negeri 1 Semarang", "address": "Jl. Taman Menteri Supeno No. 1", "city": "Semarang", "province": "Jawa Tengah", "postcode": "50134", "phone": "024-3540306", "npsn": "20329797", "domain": "sman1semarang.sch.id"},
    {"name": "SMA Negeri 5 Medan", "address": "Jl. Williem Iskandar Pasar V", "city": "Medan", "province": "Sumatera Utara", "postcode": "20222", "phone": "061-6627590", "npsn": "10210752", "domain": "sman5medan.sch.id"},
    {"name": "SMA Negeri 1 Denpasar", "address": "Jl. Pucang Gading No. 5", "city": "Denpasar", "province": "Bali", "postcode": "80226", "phone": "0361-424533", "npsn": "50100116", "domain": "sman1denpasar.sch.id"},
    {"name": "SMA Negeri 3 Malang", "address": "Jl. Sultan Agung No. 7", "city": "Malang", "province": "Jawa Timur", "postcode": "65119", "phone": "0341-326454", "npsn": "20533534", "domain": "sman3malang.sch.id"},
    {"name": "SMA Negeri 2 Palembang", "address": "Jl. Jenderal Ahmad Yani", "city": "Palembang", "province": "Sumatera Selatan", "postcode": "30126", "phone": "0711-352790", "npsn": "10604558", "domain": "sman2palembang.sch.id"},
]

# Indonesia Names
INDONESIA_FIRST_NAMES = [
    "Ahmad", "Budi", "Citra", "Dewi", "Eka", "Fitri", "Gunawan", "Hadi",
    "Indra", "Joko", "Kartika", "Lestari", "Made", "Nur", "Putra", "Rina",
    "Sari", "Taufik", "Usman", "Vera", "Wati", "Yanto", "Zahra", "Agus",
    "Dian", "Fajar", "Haryo", "Ismail", "Lina", "Maya", "Ratna", "Wulan"
]

INDONESIA_LAST_NAMES = [
    "Wijaya", "Santoso", "Kusuma", "Pratama", "Hidayat", "Setiawan", "Saputra", "Rahmawati",
    "Putra", "Putri", "Susanto", "Utomo", "Lestari", "Handayani", "Wibowo", "Suryanto",
    "Nugroho", "Kurniawan", "Hermawan", "Prasetyo", "Suharto", "Rahma", "Anggraini", "Fitria",
    "Permana", "Hakim", "Subhan", "Nurdin", "Irawan", "Mahendra", "Purnama", "Safitri"
]

# Indonesia Teaching Positions
INDONESIA_TEACHING_POSITIONS = [
    "Guru Matematika",
    "Guru Bahasa Indonesia",
    "Guru Bahasa Inggris",
    "Guru Fisika",
    "Guru Kimia",
    "Guru Biologi",
    "Guru Ekonomi",
    "Guru Sejarah",
    "Guru Geografi",
    "Guru Seni Budaya",
    "Guru Pendidikan Jasmani",
    "Guru BK (Bimbingan Konseling)",
    "Wakil Kepala Sekolah",
    "Guru Mata Pelajaran",
]


class IndonesiaGenerator(CountryGenerator):
    """Indonesia-specific document generator"""
    
    # Mapping untuk nama file yang lebih jelas
    DOCUMENT_NAMES = {
        "payslip": "Slip_Gaji",
        "teaching_experience_letter": "Surat_Keterangan_Mengajar",
        "nuptk_card": "Kartu_NUPTK",
        "appointment_letter": "SK_Pengangkatan"
    }
    
    def get_country_name(self) -> str:
        return "Indonesia"
    
    def get_country_code(self) -> str:
        return "indonesia"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_INDONESIA_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return INDONESIA_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return INDONESIA_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return INDONESIA_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["payslip", "teaching_experience_letter", "nuptk_card", "appointment_letter"]
    
    def get_document_name(self, doc_type: str) -> str:
        """Get friendly Indonesian name for document type"""
        return self.DOCUMENT_NAMES.get(doc_type, doc_type)
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Indonesia document"""
        if doc_type == "payslip":
            return self._generate_payslip(first, last, school, position)
        elif doc_type == "teaching_experience_letter":
            return self._generate_teaching_experience_letter(first, last, school, position)
        elif doc_type == "nuptk_card":
            return self._generate_nuptk_card(first, last, school, position, dob)
        elif doc_type == "appointment_letter":
            return self._generate_appointment_letter(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_payslip(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Slip Gaji (Payslip)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 56)
            font_header = load_font("arialbd", 42)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Red and white header (Indonesian flag colors)
        draw.rectangle([(0, 0), (w, 60)], fill=(220, 20, 60))
        draw.rectangle([(0, 60), (w, 120)], fill=(255, 255, 255))
        
        # Title
        y = 180
        draw.text((w//2, y), "SLIP GAJI PEGAWAI", fill=(220, 20, 60), font=font_title, anchor="mm")
        
        # School info box
        y = 280
        draw.rectangle([(150, y), (w-150, y+280)], fill=(250, 248, 245), outline=(220, 20, 60), width=4)
        
        y += 40
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"NPSN: {school['npsn']} | Telp: {school['phone']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Period info
        y += 120
        current_month = datetime.now().strftime("%B %Y")
        slip_number = f"SG/{random.randint(1000, 9999)}/{datetime.now().strftime('%m/%Y')}"
        
        info_items = [
            ("Nomor Slip:", slip_number),
            ("Periode:", current_month),
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
        draw.rectangle([(150, y), (w-150, y+60)], fill=(220, 20, 60))
        draw.text((w//2, y+30), "DATA PEGAWAI", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        nip = f"19{random.randint(70, 99)}{random.randint(10, 12)}{random.randint(10, 28)}{random.randint(100000, 999999)}"
        
        employee_data = [
            ("Nama", f"{first} {last}"),
            ("NIP", nip),
            ("Jabatan", position),
            ("Golongan/Ruang", f"III/{chr(random.randint(97, 100))}"),
        ]
        
        for label, value in employee_data:
            draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
            draw.text((700, y), value, fill=(0, 0, 0), font=font_normal)
            y += 60
        
        # Salary details
        y += 60
        draw.rectangle([(150, y), (w-150, y+60)], fill=(220, 20, 60))
        draw.text((w//2, y+30), "RINCIAN PENGHASILAN", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        base_salary = random.randint(4500000, 8500000)
        allowance = random.randint(1500000, 3000000)
        total = base_salary + allowance
        
        # Income section
        income_items = [
            ("Gaji Pokok", f"Rp {base_salary:,}"),
            ("Tunjangan Profesi", f"Rp {allowance:,}"),
            ("Tunjangan Kinerja", f"Rp {random.randint(500000, 1500000):,}"),
        ]
        
        for label, value in income_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        # Total
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(220, 20, 60), width=4)
        y += 50
        draw.text((250, y), "TOTAL PENGHASILAN BRUTO", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"Rp {total:,}", fill=(220, 20, 60), font=font_bold, anchor="ra")
        
        # Deductions
        y += 100
        draw.rectangle([(150, y), (w-150, y+60)], fill=(100, 100, 100))
        draw.text((w//2, y+30), "POTONGAN", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        deduction_items = [
            ("Iuran Wajib Pegawai (IWP)", f"Rp {int(total * 0.045):,}"),
            ("PPh Pasal 21", f"Rp {int(total * 0.05):,}"),
        ]
        
        for label, value in deduction_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        total_deduction = int(total * 0.095)
        net_salary = total - total_deduction
        
        # Net salary
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(100, 100, 100), width=4)
        y += 50
        draw.text((250, y), "PENGHASILAN BERSIH", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"Rp {net_salary:,}", fill=(0, 128, 0), font=font_bold, anchor="ra")
        
        # Signature
        y = h - 550
        draw.text((w//2, y), f"{school['city']}, {datetime.now().strftime('%d %B %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w-600, y), "Bendahara", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 150
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=2)
        y += 40
        draw.text((w-600, y), "NIP. " + nip[:18], fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 150
        draw.line([(150, y), (w-150, y)], fill=(220, 20, 60), width=3)
        y += 40
        draw.text((w//2, y), "Dokumen ini dicetak secara otomatis dan sah tanpa tanda tangan basah", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_experience_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Surat Keterangan Mengajar"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 44)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Header with Indonesian colors
        draw.rectangle([(0, 0), (w, 40)], fill=(220, 20, 60))
        draw.rectangle([(0, 40), (w, 80)], fill=(255, 255, 255))
        
        # School header
        y = 140
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Telp: {school['phone']} | NPSN: {school['npsn']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 60
        draw.rectangle([(200, y), (w-200, y+6)], fill=(220, 20, 60))
        
        # Document title
        y += 100
        draw.rectangle([(150, y), (w-150, y+100)], fill=(250, 245, 240))
        draw.text((w//2, y+50), "SURAT KETERANGAN MENGAJAR", fill=(220, 20, 60), font=font_header, anchor="mm")
        
        # Reference number
        y += 150
        ref_number = f"Nomor: {random.randint(100, 999)}/SK-Guru/{datetime.now().strftime('%m/%Y')}"
        draw.text((w//2, y), ref_number, fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Content
        y += 120
        content_lines = [
            "Yang bertanda tangan di bawah ini Kepala Sekolah",
            f"{school['name']}, menerangkan bahwa:",
        ]
        
        for line in content_lines:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55
        
        y += 50
        nuptk = f"{random.randint(1000, 9999)} {random.randint(7000, 7999)} {random.randint(6000, 6999)} {random.randint(1000, 9999)}"
        
        teacher_data = [
            ("Nama", f": {first} {last}"),
            ("NUPTK", f": {nuptk}"),
            ("Jabatan", f": {position}"),
            ("Masa Kerja", f": {random.randint(3, 15)} Tahun"),
            ("Status", f": Guru Tetap"),
        ]
        
        for label, value in teacher_data:
            draw.text((500, y), label, fill=(0, 0, 0), font=font_bold)
            draw.text((900, y), value, fill=(0, 0, 0), font=font_normal)
            y += 65
        
        y += 80
        cert_text = [
            "Yang bersangkutan adalah guru tetap di sekolah kami sejak tahun",
            f"{datetime.now().year - random.randint(3, 15)} dan masih aktif mengajar hingga saat ini.",
            "",
            "Demikian surat keterangan ini dibuat untuk dapat dipergunakan",
            "sebagaimana mestinya.",
        ]
        
        for line in cert_text:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55 if line else 30
        
        # Signature
        y += 100
        draw.text((w//2, y), f"{school['city']}, {datetime.now().strftime('%d %B %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 80
        draw.text((w-600, y), "Kepala Sekolah", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Stamp placeholder
        stamp_x = w - 600
        stamp_y = y + 120
        draw.ellipse([(stamp_x-90, stamp_y-90), (stamp_x+90, stamp_y+90)], outline=(220, 20, 60), width=8)
        draw.text((stamp_x, stamp_y), "CAP", fill=(220, 20, 60), font=font_header, anchor="mm")
        
        y += 200
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=3)
        y += 45
        draw.text((w-600, y), school['name'][:25], fill=(0, 0, 0), font=font_small, anchor="mm")
        y += 40
        draw.text((w-600, y), f"NIP. 19{random.randint(70, 85)}{random.randint(10,12)}{random.randint(10,28)} {random.randint(100000, 999999)} {random.randint(1, 2)} {random.randint(100, 999)}", 
                 fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(220, 20, 60), width=3)
        y += 45
        draw.text((w//2, y), f"Dokumen resmi {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_nuptk_card(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Kartu NUPTK - Modern version"""
        w, h = 1920, 1080
        
        # Create base with gradient background
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 48)
            font_header = load_font("arialbd", 38)
            font_name = load_font("arialbd", 42)
            font_label = load_font("arial", 26)
            font_value = load_font("arialbd", 30)
            font_small = load_font("arial", 22)
            font_tiny = load_font("arial", 18)
        except:
            font_title = font_header = font_name = font_label = font_value = font_small = font_tiny = ImageFont.load_default()
        
        # Modern gradient background
        for i in range(h):
            alpha = i / h
            r = int(245 + (255 - 245) * alpha)
            g = int(245 + (255 - 245) * alpha)
            b = int(250 + (255 - 250) * alpha)
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        
        # Top red gradient banner (Indonesian flag)
        for i in range(140):
            alpha = i / 140
            r = int(200 + (220 - 200) * (1 - alpha))
            g = int(15 + (20 - 15) * (1 - alpha))
            b = int(50 + (60 - 50) * (1 - alpha))
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        
        # White stripe
        draw.rectangle([(0, 140), (w, 200)], fill=(255, 255, 255))
        
        # Outer border with shadow effect
        shadow_offset = 8
        draw.rectangle([(shadow_offset, shadow_offset), (w-10+shadow_offset, h-10+shadow_offset)], 
                      fill=(200, 200, 200))
        draw.rectangle([(10, 10), (w-10, h-10)], fill=(255, 255, 255), outline=(220, 20, 60), width=8)
        draw.rectangle([(20, 20), (w-20, h-20)], outline=(180, 140, 40), width=3)
        
        # Watermark pattern
        for i in range(0, w, 100):
            for j in range(250, h-100, 100):
                draw.text((i, j), "★", fill=(240, 240, 245), font=font_header, anchor="mm")
        
        # Logo and title section
        y = 50
        draw.text((w//2, y), "REPUBLIK INDONESIA", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y = 160
        draw.text((w//2, y), "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET, DAN TEKNOLOGI", 
                 fill=(40, 40, 40), font=font_small, anchor="mm")
        
        # Main title with background
        y = 230
        title_bg_y = y - 35
        draw.rectangle([(100, title_bg_y), (w-100, title_bg_y+70)], fill=(220, 20, 60))
        draw.text((w//2, y), "KARTU NOMOR UNIK PENDIDIK DAN TENAGA KEPENDIDIKAN", 
                 fill=(255, 255, 255), font=font_title, anchor="mm")
        
        y += 50
        draw.text((w//2, y), "NUPTK CARD", fill=(100, 100, 100), font=font_label, anchor="mm")
        
        # Photo section with modern frame
        photo_size = (280, 350)
        photo_x, photo_y = 80, 350
        
        # Photo shadow
        shadow_box = (photo_x+5, photo_y+5, photo_x+photo_size[0]+5, photo_y+photo_size[1]+5)
        draw.rectangle(shadow_box, fill=(180, 180, 180))
        
        # Photo background
        photo_bg = (photo_x-10, photo_y-10, photo_x+photo_size[0]+10, photo_y+photo_size[1]+10)
        draw.rectangle(photo_bg, fill=(255, 255, 255), outline=(220, 20, 60), width=6)
        
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(220, 20, 60))
        
        img.paste(photo, (photo_x, photo_y))
        
        # Photo inner border
        draw.rectangle([(photo_x, photo_y), (photo_x+photo_size[0], photo_y+photo_size[1])], 
                      outline=(180, 140, 40), width=3)
        
        # NUPTK Number Box (prominent)
        nuptk_box_y = 340
        nuptk = f"{random.randint(1000, 9999)} {random.randint(7000, 7999)} {random.randint(6000, 6999)} {random.randint(1000, 9999)}"
        
        draw.rectangle([(400, nuptk_box_y), (w-80, nuptk_box_y+100)], fill=(250, 248, 245), 
                      outline=(220, 20, 60), width=4)
        draw.rectangle([(400, nuptk_box_y), (w-80, nuptk_box_y+40)], fill=(220, 20, 60))
        draw.text((w//2+160, nuptk_box_y+20), "NUPTK", fill=(255, 255, 255), 
                 font=font_header, anchor="mm")
        draw.text((w//2+160, nuptk_box_y+70), nuptk, fill=(220, 20, 60), 
                 font=font_title, anchor="mm")
        
        # Personal information section
        info_x = 420
        y = 470
        
        nip = f"19{random.randint(75, 95)}{random.randint(10,12)}{random.randint(10,28)} {random.randint(100000, 999999)} {random.randint(1, 2)} {random.randint(100, 999)}"
        
        info_items = [
            ("NAMA LENGKAP", f"{first} {last}".upper()),
            ("NIK/NIP", nip),
            ("TEMPAT, TGL LAHIR", f"{random.choice(['Jakarta', 'Bandung', 'Surabaya', 'Semarang', 'Yogyakarta'])}, {dob}"),
            ("JENIS KELAMIN", random.choice(["LAKI-LAKI", "PEREMPUAN"])),
            ("INSTANSI", school["name"].upper()),
            ("JABATAN", position.upper()),
            ("STATUS", "AKTIF"),
        ]
        
        for label, value in info_items:
            # Label background
            draw.rectangle([(info_x, y), (info_x+280, y+32)], fill=(240, 240, 245))
            draw.text((info_x+10, y+16), label, fill=(100, 100, 100), font=font_label, anchor="lm")
            y += 38
            draw.text((info_x+10, y+8), value, fill=(0, 0, 0), font=font_value, anchor="lm")
            y += 48
        
        # QR Code placeholder (modern touch)
        qr_x, qr_y = 80, 750
        qr_size = 180
        draw.rectangle([(qr_x, qr_y), (qr_x+qr_size, qr_y+qr_size)], fill=(255, 255, 255), 
                      outline=(0, 0, 0), width=4)
        
        # QR pattern simulation
        grid_size = 12
        cell_size = qr_size // grid_size
        for i in range(grid_size):
            for j in range(grid_size):
                if random.choice([True, False]):
                    cx = qr_x + i * cell_size
                    cy = qr_y + j * cell_size
                    draw.rectangle([(cx, cy), (cx+cell_size-1, cy+cell_size-1)], fill=(0, 0, 0))
        
        draw.text((qr_x+qr_size//2, qr_y+qr_size+20), "SCAN ME", fill=(100, 100, 100), 
                 font=font_small, anchor="mm")
        
        # Validity and signature section
        valid_x = 320
        valid_y = 760
        
        issue_date = datetime.now().strftime("%d-%m-%Y")
        expiry_date = f"{datetime.now().day:02d}-{datetime.now().month:02d}-{datetime.now().year + 5}"
        
        draw.rectangle([(valid_x, valid_y), (valid_x+520, valid_y+160)], fill=(255, 255, 255), 
                      outline=(180, 140, 40), width=3)
        
        y = valid_y + 25
        draw.text((valid_x+260, y), "MASA BERLAKU KARTU", fill=(100, 100, 100), 
                 font=font_label, anchor="mm")
        y += 35
        draw.text((valid_x+130, y), "Tanggal Terbit:", fill=(60, 60, 60), font=font_small, anchor="mm")
        draw.text((valid_x+390, y), "Tanggal Berakhir:", fill=(60, 60, 60), font=font_small, anchor="mm")
        y += 30
        draw.text((valid_x+130, y), issue_date, fill=(220, 20, 60), font=font_value, anchor="mm")
        draw.text((valid_x+390, y), expiry_date, fill=(220, 20, 60), font=font_value, anchor="mm")
        
        # Official stamp placeholder
        stamp_x, stamp_y = w - 250, 800
        draw.ellipse([(stamp_x-70, stamp_y-70), (stamp_x+70, stamp_y+70)], 
                    outline=(220, 20, 60), width=6)
        draw.ellipse([(stamp_x-55, stamp_y-55), (stamp_x+55, stamp_y+55)], 
                    outline=(220, 20, 60), width=2)
        draw.text((stamp_x, stamp_y-10), "KEMENDIKBUD", fill=(220, 20, 60), 
                 font=font_small, anchor="mm")
        draw.text((stamp_x, stamp_y+15), "RISTEK", fill=(220, 20, 60), 
                 font=font_small, anchor="mm")
        
        # Security features text
        y = h - 80
        draw.line([(50, y), (w-50, y)], fill=(200, 200, 200), width=2)
        y += 25
        draw.text((w//2, y), "Kartu ini dilindungi hologram dan watermark • Dokumen Resmi Pemerintah RI", 
                 fill=(120, 120, 120), font=font_tiny, anchor="mm")
        y += 25
        serial = f"ID-NUPTK-{random.randint(100000, 999999)}-{datetime.now().year}"
        draw.text((w//2, y), f"Serial: {serial}", 
                 fill=(150, 150, 150), font=font_tiny, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_appointment_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate SK Pengangkatan"""
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
        
        # Header
        draw.rectangle([(0, 0), (w, 50)], fill=(220, 20, 60))
        draw.rectangle([(0, 50), (w, 100)], fill=(255, 255, 255))
        
        y = 160
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['city']}, {school['province']} - {school['postcode']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 70
        draw.rectangle([(200, y), (w-200, y+8)], fill=(220, 20, 60))
        
        # Title
        y += 100
        draw.rectangle([(150, y), (w-150, y+120)], fill=(255, 245, 240))
        draw.text((w//2, y+60), "SURAT KEPUTUSAN PENGANGKATAN", fill=(220, 20, 60), font=font_header, anchor="mm")
        
        y += 180
        sk_number = f"Nomor: {random.randint(100, 999)}/SK-Guru/{datetime.now().year}"
        draw.text((w//2, y), sk_number, fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 100
        lines = [
            "TENTANG",
            f"PENGANGKATAN {position.upper()}",
            f"DI {school['name'].upper()}",
        ]
        
        for line in lines:
            draw.text((w//2, y), line, fill=(0, 0, 0), font=font_bold, anchor="mm")
            y += 60
        
        y += 80
        content = [
            "KEPALA SEKOLAH",
            "",
            "Menimbang:",
            f"a. Bahwa untuk kelancaran proses pembelajaran di {school['name']},",
            "   diperlukan tenaga pengajar yang berkualitas;",
            f"b. Bahwa Saudara/i {first} {last} dipandang memenuhi syarat",
            "   untuk diangkat sebagai guru tetap;",
            "",
            "Memutuskan:",
            "",
            f"Pasal 1",
            f"Mengangkat: {first} {last}",
            f"Sebagai: {position}",
            f"Status: Guru Tetap",
            f"TMT: 01 Juli {datetime.now().year - random.randint(1, 10)}",
            "",
            "Pasal 2",
            "Surat Keputusan ini berlaku sejak tanggal ditetapkan dengan",
            "ketentuan apabila dikemudian hari terdapat kekeliruan akan",
            "diadakan pembetulan sebagaimana mestinya.",
        ]
        
        for line in content:
            if "Pasal" in line or "KEPALA" in line or "Menimbang" in line or "Memutuskan" in line:
                draw.text((w//2, y), line, fill=(220, 20, 60), font=font_bold, anchor="mm")
                y += 70
            elif line:
                draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
                y += 52
            else:
                y += 30
        
        # Signature
        y = h - 600
        draw.text((w//2, y), f"Ditetapkan di: {school['city']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"Pada tanggal: {datetime.now().strftime('%d %B %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w-600, y), "Kepala Sekolah", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Stamp
        stamp_x = w - 600
        stamp_y = y + 120
        draw.ellipse([(stamp_x-90, stamp_y-90), (stamp_x+90, stamp_y+90)], outline=(220, 20, 60), width=8)
        draw.ellipse([(stamp_x-70, stamp_y-70), (stamp_x+70, stamp_y+70)], outline=(0, 0, 0), width=4)
        draw.text((stamp_x, stamp_y), school["name"][:4].upper(), fill=(220, 20, 60), font=font_bold, anchor="mm")
        
        y += 200
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=3)
        y += 45
        draw.text((w-600, y), f"NIP. 19{random.randint(70, 85)}{random.randint(10,12)}{random.randint(10,28)} {random.randint(100000, 999999)} {random.randint(1, 2)} {random.randint(100, 999)}", 
                 fill=(80, 80, 80), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
