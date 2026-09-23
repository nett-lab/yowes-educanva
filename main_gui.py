"""
Canva Education Document Generator - Modern GUI
Modern UI/UX with CustomTkinter
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import sys
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
import threading

try:
    from PIL import Image, ImageTk
except ImportError:
    pass  # Will be checked at runtime

from countries import get_country, list_countries

# ============ CONFIG ============
ctk.set_appearance_mode("dark")  # "dark", "light", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class CanvaEducationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("📚 Canva Education - Document Generator")
        self.geometry("1000x700")
        self.minsize(900, 650)
        
        # Variables
        self.country_var = ctk.StringVar(value="uk")
        self.doc_type_var = ctk.StringVar(value="all")
        self.first_name_var = ctk.StringVar()
        self.last_name_var = ctk.StringVar()
        self.school_var = ctk.StringVar()
        self.position_var = ctk.StringVar()
        self.auto_generate_var = ctk.BooleanVar(value=True)
        
        # Generator
        self.generator = None
        
        # Setup UI first (creates all widgets)
        self.setup_ui()
        
        # Load generator after UI is ready
        self.load_generator()
        
        # Update info on start
        self.on_country_change()
        
    def setup_ui(self):
        """Setup the main UI"""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.create_header()
        
        # Main container
        main_container = ctk.CTkFrame(self)
        main_container.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        
        # Left panel - Configuration
        self.create_left_panel(main_container)
        
        # Right panel - Preview & Output
        self.create_right_panel(main_container)
        
        # Footer
        self.create_footer()
        
    def create_header(self):
        """Create header with title and theme switcher"""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="📚 Canva Education Document Generator",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, pady=(0, 5))
        
        subtitle = ctk.CTkLabel(
            header,
            text="Generate teacher verification documents for Canva Education",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        subtitle.grid(row=1, column=0)
        
        # Theme switcher
        theme_frame = ctk.CTkFrame(header, fg_color="transparent")
        theme_frame.grid(row=0, column=2, rowspan=2, padx=10)
        
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
        
        theme_switch = ctk.CTkSegmentedButton(
            theme_frame,
            values=["Light", "Dark", "System"],
            command=self.change_theme,
            width=200
        )
        theme_switch.set("Dark")
        theme_switch.pack(side="left")
        
    def create_left_panel(self, parent):
        """Create left configuration panel"""
        left_panel = ctk.CTkScrollableFrame(parent, width=380)
        left_panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)
        
        # ===== Country Selection =====
        country_frame = ctk.CTkFrame(left_panel)
        country_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        country_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            country_frame,
            text="🌍 Country Selection",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(country_frame, text="Country:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.country_combo = ctk.CTkComboBox(
            country_frame,
            variable=self.country_var,
            values=self.get_country_list(),
            command=lambda x: self.on_country_change(),
            width=200
        )
        self.country_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Country info
        self.country_info_label = ctk.CTkLabel(
            country_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        self.country_info_label.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # ===== Document Type =====
        doc_frame = ctk.CTkFrame(left_panel)
        doc_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        doc_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            doc_frame,
            text="📄 Document Type",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(doc_frame, text="Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.doc_type_combo = ctk.CTkComboBox(
            doc_frame,
            variable=self.doc_type_var,
            values=["all"],
            width=200
        )
        self.doc_type_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Document type info
        self.doc_info_label = ctk.CTkLabel(
            doc_frame,
            text="Generate all document types",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=320,
            justify="left"
        )
        self.doc_info_label.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # ===== Personal Information =====
        personal_frame = ctk.CTkFrame(left_panel)
        personal_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        personal_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            personal_frame,
            text="👤 Personal Information",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        # Auto-generate checkbox
        self.auto_check = ctk.CTkCheckBox(
            personal_frame,
            text="Auto-generate random data",
            variable=self.auto_generate_var,
            command=self.toggle_auto_generate,
            font=ctk.CTkFont(size=13)
        )
        self.auto_check.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # First name
        ctk.CTkLabel(personal_frame, text="First Name:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.first_name_entry = ctk.CTkEntry(personal_frame, textvariable=self.first_name_var, width=200)
        self.first_name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Last name
        ctk.CTkLabel(personal_frame, text="Last Name:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.last_name_entry = ctk.CTkEntry(personal_frame, textvariable=self.last_name_var, width=200)
        self.last_name_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Gender (NEW)
        ctk.CTkLabel(personal_frame, text="Gender:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.gender_var = ctk.StringVar(value="Random")
        gender_combo = ctk.CTkComboBox(
            personal_frame,
            variable=self.gender_var,
            values=["Random", "Male", "Female"],
            state="readonly",
            width=200
        )
        gender_combo.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # School
        ctk.CTkLabel(personal_frame, text="School:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        
        school_container = ctk.CTkFrame(personal_frame, fg_color="transparent")
        school_container.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        school_container.grid_columnconfigure(0, weight=1)
        
        self.school_entry = ctk.CTkEntry(school_container, textvariable=self.school_var)
        self.school_entry.grid(row=0, column=0, sticky="ew")
        
        self.school_list_btn = ctk.CTkButton(
            school_container,
            text="📋",
            width=30,
            command=self.show_school_list
        )
        self.school_list_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Position
        ctk.CTkLabel(personal_frame, text="Position:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.position_entry = ctk.CTkEntry(personal_frame, textvariable=self.position_var, width=200)
        self.position_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        # Random button
        random_btn = ctk.CTkButton(
            personal_frame,
            text="🎲 Generate Random Data",
            command=self.generate_random_data,
            fg_color="green",
            hover_color="darkgreen"
        )
        random_btn.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # ===== Action Buttons =====
        action_frame = ctk.CTkFrame(left_panel)
        action_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        
        # Generate button
        self.generate_btn = ctk.CTkButton(
            action_frame,
            text="✨ Generate Documents",
            command=self.generate_documents,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#1f538d",
            hover_color="#14375e"
        )
        self.generate_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Open output folder
        open_folder_btn = ctk.CTkButton(
            action_frame,
            text="📁 Open Output Folder",
            command=self.open_output_folder,
            font=ctk.CTkFont(size=14),
            height=35
        )
        open_folder_btn.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(action_frame)
        self.progress.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progress.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            action_frame,
            text="Ready to generate",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10))
        
        # Toggle auto-generate state
        self.toggle_auto_generate()
        
    def create_right_panel(self, parent):
        """Create right panel for preview and output"""
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)
        
        # Title
        ctk.CTkLabel(
            right_panel,
            text="📋 Output & Information",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Tab view
        self.tabview = ctk.CTkTabview(right_panel)
        self.tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Output tab
        self.tabview.add("📄 Output Log")
        output_tab = self.tabview.tab("📄 Output Log")
        output_tab.grid_columnconfigure(0, weight=1)
        output_tab.grid_rowconfigure(0, weight=1)
        
        self.output_text = ctk.CTkTextbox(output_tab, wrap="word", font=ctk.CTkFont(size=12))
        self.output_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Info tab
        self.tabview.add("ℹ️ About")
        info_tab = self.tabview.tab("ℹ️ About")
        info_tab.grid_columnconfigure(0, weight=1)
        info_tab.grid_rowconfigure(0, weight=1)
        
        info_text = ctk.CTkTextbox(info_tab, wrap="word", font=ctk.CTkFont(size=12))
        info_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        info_text.insert("1.0", self.get_about_text())
        info_text.configure(state="disabled")
        
        # Files tab
        self.tabview.add("📁 Generated Files")
        files_tab = self.tabview.tab("📁 Generated Files")
        files_tab.grid_columnconfigure(0, weight=1)
        files_tab.grid_rowconfigure(1, weight=1)
        
        # Files list area
        self.files_listbox = ctk.CTkTextbox(files_tab, wrap="word", font=ctk.CTkFont(size=12))
        self.files_listbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Buttons frame for file operations
        files_btn_frame = ctk.CTkFrame(files_tab, fg_color="transparent")
        files_btn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        files_btn_frame.grid_columnconfigure(1, weight=1)
        
        self.delete_file_btn = ctk.CTkButton(
            files_btn_frame,
            text="🗑️ Delete Selected",
            command=self.delete_selected_file,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=150
        )
        self.delete_file_btn.grid(row=0, column=0, padx=5)
        
        self.clear_all_btn = ctk.CTkButton(
            files_btn_frame,
            text="🗑️ Clear All Files",
            command=self.clear_all_files,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=150
        )
        self.clear_all_btn.grid(row=0, column=1, padx=5)
        
        self.refresh_files_btn = ctk.CTkButton(
            files_btn_frame,
            text="🔄 Refresh List",
            command=self.refresh_files_list,
            width=120
        )
        self.refresh_files_btn.grid(row=0, column=2, padx=5)
        
        # Store generated files list
        self.generated_files_list = []
        
        # Initial log
        self.log("Welcome to Canva Education Document Generator!")
        self.log("Select a country and configure options to get started.")
        self.log("=" * 50)
        
    def create_footer(self):
        """Create footer"""
        footer = ctk.CTkFrame(self, height=30, fg_color="transparent")
        footer.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(
            footer,
            text="© 2026 Canva Education Document Generator | MasantoID",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack()
        
    # ===== Helper Methods =====
    
    def get_country_list(self):
        """Get formatted country list"""
        countries = []
        country_names = {
            "uk": "🇬🇧 United Kingdom",
            "france": "🇫🇷 France",
            "netherlands": "🇳🇱 Netherlands",
            "spain": "🇪🇸 Spain",
            "indonesia": "🇮🇩 Indonesia",
            "argentina": "🇦🇷 Argentina",
            "australia": "🇦🇺 Australia",
            "canada": "🇨🇦 Canada",
            "slovakia": "🇸🇰 Slovakia",
            "mexico": "🇲🇽 Mexico",
            "philippines": "🇵🇭 Philippines",
            "thailand": "🇹🇭 Thailand",
            "us": "🇺🇸 United States"
        }
        
        for code in list_countries():
            display = country_names.get(code, f"🌍 {code.upper()}")
            countries.append(display)
        
        return countries
    
    def load_generator(self):
        """Load country generator"""
        try:
            country_code = self.country_var.get().split()[1].lower() if len(self.country_var.get().split()) > 1 else self.country_var.get()
            GeneratorClass = get_country(country_code)
            self.generator = GeneratorClass()
        except:
            # Default to UK
            try:
                GeneratorClass = get_country("uk")
                self.generator = GeneratorClass()
            except:
                pass
    
    def on_country_change(self, *args):
        """Handle country change"""
        # Extract country code from display text (e.g., "🇬🇧 United Kingdom" -> "uk")
        country_display = self.country_var.get()
        country_mapping = {
            "🇬🇧 United Kingdom": "uk",
            "🇫🇷 France": "france",
            "🇳🇱 Netherlands": "netherlands",
            "🇪🇸 Spain": "spain",
            "🇮🇩 Indonesia": "indonesia",
            "🇦🇷 Argentina": "argentina",
            "🇦🇺 Australia": "australia",
            "🇨🇦 Canada": "canada",
            "🇸🇰 Slovakia": "slovakia",
            "🇲🇽 Mexico": "mexico",
            "🇵🇭 Philippines": "philippines",
            "🇹🇭 Thailand": "thailand",
            "🇺🇸 United States": "us"
        }
        
        country_code = country_mapping.get(country_display, country_display)
        
        try:
            GeneratorClass = get_country(country_code)
            self.generator = GeneratorClass()
            
            # Update document types
            doc_types = ["all"] + self.generator.get_document_types()
            self.doc_type_combo.configure(values=doc_types)
            self.doc_type_var.set("all")
            
            # Update country info
            info = f"Selected: {self.generator.get_country_name()}\n"
            info += f"Available documents: {len(doc_types) - 1}"
            self.country_info_label.configure(text=info)
            
            # Clear and regenerate random data
            if self.auto_generate_var.get():
                self.generate_random_data()
            
            self.log(f"✓ Loaded {self.generator.get_country_name()} generator")
            
        except Exception as e:
            self.log(f"✗ Error loading country: {e}", "error")
    
    def toggle_auto_generate(self):
        """Toggle auto-generate mode"""
        enabled = not self.auto_generate_var.get()
        
        self.first_name_entry.configure(state="normal" if enabled else "disabled")
        self.last_name_entry.configure(state="normal" if enabled else "disabled")
        self.position_entry.configure(state="normal" if enabled else "disabled")
        
        # School entry & list button always enabled so user can always pick a school
        self.school_entry.configure(state="normal")
        self.school_list_btn.configure(state="normal")
        
        if not enabled:
            self.generate_random_data()
    
    def generate_random_data(self):
        """Generate random personal data"""
        if not self.generator:
            return
        
        first, last = self.generator.generate_name()
        school = self.generator.random_school()
        position = random.choice(self.generator.get_positions())
        
        self.first_name_var.set(first)
        self.last_name_var.set(last)
        self.school_var.set(school["name"])
        self.position_var.set(position)
        
        self.log(f"🎲 Generated random data: {first} {last}")
    
    def show_school_list(self):
        """Show list of available schools"""
        if not self.generator:
            return
        
        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select School")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="Available Schools",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(padx=20, pady=10)
        
        # List frame
        list_frame = ctk.CTkScrollableFrame(dialog)
        list_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        schools = self.generator.list_schools()
        for i, school_name in enumerate(schools):
            btn = ctk.CTkButton(
                list_frame,
                text=f"{i+1}. {school_name}",
                command=lambda s=school_name: self.select_school(s, dialog),
                anchor="w"
            )
            btn.pack(padx=5, pady=2, fill="x")
        
        close_btn = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(padx=20, pady=10)
    
    def select_school(self, school_name, dialog):
        """Select a school from list"""
        self.school_var.set(school_name)
        dialog.destroy()
        self.log(f"✓ Selected school: {school_name}")
    
    def generate_documents(self):
        """Generate documents"""
        if not self.generator:
            messagebox.showerror("Error", "No country generator loaded!")
            return
        
        # Disable button during generation
        self.generate_btn.configure(state="disabled", text="⏳ Generating...")
        self.progress.set(0)
        
        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self._generate_documents_thread, daemon=True)
        thread.start()
    
    def _generate_documents_thread(self):
        """Thread for document generation"""
        try:
            # Clear photo cache untuk session baru
            from countries.utils import clear_photo_cache
            clear_photo_cache()
            
            # Get parameters
            first = self.first_name_var.get()
            last = self.last_name_var.get()
            school_name = self.school_var.get()
            position = self.position_var.get()
            doc_type = self.doc_type_var.get()
            gender = self.gender_var.get()
            
            # Create person_id for consistent photos
            person_id = f"{first.lower()}_{last.lower()}"
            
            # Store person_id and gender in generator for use in documents
            self.generator._current_person_id = person_id
            self.generator._current_gender = gender
            
            # Find school
            school = None
            for s in self.generator.get_schools_data():
                if s["name"] == school_name:
                    school = s
                    break
            
            if not school:
                school = self.generator.random_school()
            
            # Generate DOB
            dob = self.generate_dob()
            
            self.log("=" * 50)
            self.log(f"🚀 Starting document generation...")
            self.log(f"   👤 Name: {first} {last} ({gender})")
            self.log(f"   🏫 School: {school['name']}")
            
            # Show school details (address, postcode, etc)
            if 'address' in school:
                self.log(f"   📍 Address: {school['address']}")
            if 'town' in school:
                self.log(f"   🏙️  City: {school['town']}")
            elif 'city' in school:
                self.log(f"   🏙️  City: {school['city']}")
            if 'postcode' in school:
                self.log(f"   📮 Postcode/ZIP: {school['postcode']}")
            if 'state' in school:
                self.log(f"   🗺️  State: {school['state']}")
            if 'phone' in school:
                self.log(f"   📞 Phone: {school['phone']}")
            
            self.log(f"   💼 Position: {position}")
            self.log(f"   📄 Document Type: {doc_type}")
            self.log(f"   📅 Date of Birth: {dob}")
            self.log("=" * 50)
            
            # Generate documents
            if doc_type == "all":
                doc_types = self.generator.get_document_types()
            else:
                doc_types = [doc_type]
            
            total = len(doc_types)
            generated_files = []
            
            for idx, dtype in enumerate(doc_types):
                progress = (idx + 1) / total
                self.progress.set(progress)
                self.update_status(f"Generating {dtype}... ({idx+1}/{total})")
                
                try:
                    # Generate document (returns bytes)
                    doc_bytes = self.generator.generate_document(
                        doc_type=dtype,
                        first=first,
                        last=last,
                        school=school,
                        position=position,
                        dob=dob
                    )
                    
                    if doc_bytes:
                        # Create filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        country_code = self.generator.get_country_code()
                        filename = f"{country_code}_{dtype}_{first.lower()}_{last.lower()}_{timestamp}.png"
                        file_path = OUTPUT_DIR / filename
                        
                        # Save bytes to file
                        file_path.write_bytes(doc_bytes)
                        
                        generated_files.append(str(file_path))
                        self.log(f"   ✓ Generated: {dtype} -> {filename}")
                    
                except Exception as e:
                    self.log(f"   ✗ Error generating {dtype}: {e}", "error")
            
            # Complete
            self.log("=" * 50)
            self.log(f"✅ Generation complete! {len(generated_files)}/{total} documents created.")
            self.log(f"📁 Output folder: {OUTPUT_DIR}")
            self.log("=" * 50)
            
            # Update files list
            self.update_files_list(generated_files)
            
            # Show success message
            self.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Generated {len(generated_files)} document(s)!\n\nCheck output folder for files."
            ))
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"✗ Generation failed: {error_msg}", "error")
            self.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Generation failed:\n{msg}"))
        
        finally:
            # Re-enable button
            self.after(0, lambda: self.generate_btn.configure(state="normal", text="✨ Generate Documents"))
            self.after(0, lambda: self.progress.set(1))
            self.after(0, lambda: self.update_status("Ready"))
    
    def generate_dob(self, min_age=28, max_age=55):
        """Generate date of birth"""
        today = datetime.now()
        age = random.randint(min_age, max_age)
        birth_year = today.year - age
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        return f"{birth_day:02d}/{birth_month:02d}/{birth_year}"
    
    def update_files_list(self, files):
        """Update generated files list"""
        # Store files list
        self.generated_files_list = files if files else []
        
        self.files_listbox.configure(state="normal")
        self.files_listbox.delete("1.0", "end")
        
        if files:
            self.files_listbox.insert("1.0", "Recently Generated Files:\n")
            self.files_listbox.insert("end", "(Click number to select for deletion)\n\n")
            for i, file in enumerate(files, 1):
                filename = Path(file).name
                self.files_listbox.insert("end", f"{i}. {filename}\n")
                self.files_listbox.insert("end", f"   📁 {file}\n\n")
        else:
            self.files_listbox.insert("1.0", "No files generated yet.\n\n")
            self.files_listbox.insert("end", "Generate documents to see them listed here.")
        
        self.files_listbox.configure(state="disabled")
    
    def delete_selected_file(self):
        """Delete selected file from list"""
        if not self.generated_files_list:
            messagebox.showinfo("Info", "No files to delete.")
            return
        
        # Create selection dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete File")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(
            dialog,
            text="Select file to delete:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=15)
        
        # Scrollable frame for file list
        list_frame = ctk.CTkScrollableFrame(dialog, width=550, height=350)
        list_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        selected_file = ctk.StringVar()
        
        for i, file_path in enumerate(self.generated_files_list):
            filename = Path(file_path).name
            
            radio = ctk.CTkRadioButton(
                list_frame,
                text=f"{i+1}. {filename}",
                variable=selected_file,
                value=file_path,
                font=ctk.CTkFont(size=13)
            )
            radio.pack(padx=10, pady=5, anchor="w")
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(padx=20, pady=10, fill="x")
        
        def confirm_delete():
            file_to_delete = selected_file.get()
            if not file_to_delete:
                messagebox.showwarning("Warning", "Please select a file to delete.")
                return
            
            try:
                # Delete the file
                Path(file_to_delete).unlink()
                
                # Remove from list
                self.generated_files_list.remove(file_to_delete)
                
                # Update display
                self.update_files_list(self.generated_files_list)
                
                self.log(f"🗑️ Deleted: {Path(file_to_delete).name}")
                dialog.destroy()
                messagebox.showinfo("Success", f"File deleted successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file:\n{e}")
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ Delete",
            command=confirm_delete,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            width=120
        ).pack(side="left", padx=5)
    
    def clear_all_files(self):
        """Clear all generated files"""
        if not self.generated_files_list:
            messagebox.showinfo("Info", "No files to clear.")
            return
        
        # Confirmation dialog
        response = messagebox.askyesno(
            "Confirm Clear All",
            f"Are you sure you want to delete all {len(self.generated_files_list)} file(s)?\n\n"
            "This action cannot be undone!",
            icon="warning"
        )
        
        if not response:
            return
        
        deleted_count = 0
        failed_count = 0
        
        for file_path in self.generated_files_list[:]:  # Copy list to avoid modification during iteration
            try:
                Path(file_path).unlink()
                deleted_count += 1
            except Exception as e:
                self.log(f"✗ Failed to delete {Path(file_path).name}: {e}", "error")
                failed_count += 1
        
        # Clear the list
        self.generated_files_list = []
        self.update_files_list([])
        
        # Show result
        if failed_count == 0:
            self.log(f"🗑️ Successfully deleted all {deleted_count} file(s)")
            messagebox.showinfo("Success", f"All {deleted_count} file(s) deleted successfully!")
        else:
            self.log(f"⚠️ Deleted {deleted_count} file(s), {failed_count} failed", "warning")
            messagebox.showwarning("Partial Success", 
                f"Deleted {deleted_count} file(s)\nFailed to delete {failed_count} file(s)")
    
    def refresh_files_list(self):
        """Refresh files list from output folder"""
        try:
            # Get all files from output folder
            files = []
            if OUTPUT_DIR.exists():
                for file in OUTPUT_DIR.glob("*.png"):
                    files.append(str(file))
                for file in OUTPUT_DIR.glob("*.pdf"):
                    files.append(str(file))
                for file in OUTPUT_DIR.glob("*.jpg"):
                    files.append(str(file))
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
            
            # Update list
            self.generated_files_list = files
            self.update_files_list(files)
            
            self.log(f"🔄 Refreshed file list: {len(files)} file(s) found")
            
        except Exception as e:
            self.log(f"✗ Error refreshing files: {e}", "error")
            messagebox.showerror("Error", f"Failed to refresh file list:\n{e}")
    
    def open_output_folder(self):
        """Open output folder"""
        try:
            os.startfile(OUTPUT_DIR)
            self.log(f"📁 Opened output folder: {OUTPUT_DIR}")
        except Exception as e:
            self.log(f"✗ Error opening folder: {e}", "error")
            messagebox.showerror("Error", f"Could not open folder:\n{e}")
    
    def update_status(self, text):
        """Update status label"""
        self.status_label.configure(text=text)
    
    def log(self, message, level="info"):
        """Log message to output"""
        # Check if output_text exists yet
        if not hasattr(self, 'output_text'):
            print(f"[LOG] {message}")  # Print to console if UI not ready
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding
        if level == "error":
            prefix = "❌"
        elif level == "success":
            prefix = "✅"
        elif level == "warning":
            prefix = "⚠️"
        else:
            prefix = "ℹ️"
        
        log_message = f"[{timestamp}] {prefix} {message}\n"
        
        self.output_text.configure(state="normal")
        self.output_text.insert("end", log_message)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")
    
    def change_theme(self, value):
        """Change appearance theme"""
        mode = value.lower()
        ctk.set_appearance_mode(mode)
        self.log(f"🎨 Theme changed to: {value}")
    
    def get_about_text(self):
        """Get about text"""
        return """
Canva Education Document Generator
Version 2.0

📚 About This Application:
This tool generates authentic-looking teacher verification documents
for Canva Education across multiple countries. Each country has its
own specific document types and requirements.

🌍 Supported Countries:
• United Kingdom - Employment Letter, Teacher ID, QTS Certificate
• France - Installation Statement, iProf Screenshot, Collective By-laws
• Netherlands - Employment Contract, Teacher Registration, Certificate of Good Conduct
• Spain - Teaching Certificate, Employment Certificate, Payroll
• Indonesia - Payslip, Teaching Experience Letter, NUPTK Card, Appointment Letter
• Argentina - Teaching Certificate, Employment Certificate, Payroll
• Australia - Teaching Certificate, Employment Letter
• Canada - Teaching Certificate, Employment Letter
• Slovakia - Teaching Certificate, Employment Certificate
• Mexico - Teaching Certificate, Employment Certificate
• Philippines - Teaching Certificate, Employment Certificate
• Thailand - Teacher License Card, Employment Certificate, School ID Card

✨ Features:
• Intuitive interface with CustomTkinter
• Dark/Light theme support
• Auto-generate random teacher data
• Multi-country support with extensible architecture
• Real-time progress tracking
• Output file management

⚡ How to Use:
1. Select your target country from the dropdown
2. Choose document type (or "all" to generate everything)
3. Auto-generate random data or input manually
4. Click "Generate Documents" button
5. Check the output folder for your files

📝 Note:
All generated documents are for educational and testing purposes.
Please use responsibly and in accordance with applicable laws.

🔧 Technology Stack:
• Python 3.x
• CustomTkinter
• Pillow (Image processing)

💡 Tips:
• Use the 🎲 button to quickly generate random data
• Click 📋 next to school field to browse available schools
• Check the Output Log tab for detailed generation progress
• Generated files are saved in the output/ folder

Made with ❤️ by MasantoID
        """


def main():
    try:
        app = CanvaEducationGUI()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application failed to start:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
