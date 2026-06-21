import os
import json
import sys
import threading
import datetime
import ffmpeg
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- APP CONFIGURATION ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_MAIN = "#090b14"
BG_SIDEBAR = "#11131e"
BG_CARD = "#1a1d2d"
ACCENT_BLUE = "#3b82f6"
ACCENT_PURPLE = "#8b5cf6"
TEXT_MUTED = "#8b949e"

IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.ico']
VIDEO_FORMATS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.mp3', '.wav', '.flac']


def bundled_path(filename):
    """Return a resource path that works in source and PyInstaller builds."""
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


APP_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "OmniConvert",
)
CONFIG_FILE = os.path.join(APP_DATA_DIR, "omni_config.json")
FFMPEG_EXE = bundled_path(os.path.join("bin", "ffmpeg.exe"))

class OmniConvertDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OmniConvert Pro")
        self.geometry("1100x700")
        self.configure(fg_color=BG_MAIN)
        
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=280)
        self.grid_rowconfigure(0, weight=1)

        # Core Variables
        self.current_mode = "image"
        self.input_filepath = ""
        self.file_type = None 
        
        # Load Memory!
        self.output_directory = "" 
        self.history_logs = []
        self.load_memory()

        # UI References
        self.nav_buttons = {}

        self.build_left_sidebar()
        self.build_main_area() 
        self.build_right_sidebar()

        self.after(500, self.check_first_boot)

    # ==========================================
    # DATA MEMORY (NEW!)
    # ==========================================
    def load_memory(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.output_directory = data.get("output_directory", "")
                    self.history_logs = data.get("history_logs", [])
            except:
                pass # If file is corrupted, just start fresh

    def save_memory(self):
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "output_directory": self.output_directory,
                "history_logs": self.history_logs
            }, f)

    # ==========================================
    # 1. UI: LEFT SIDEBAR & NAVIGATION
    # ==========================================
    def build_left_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")

        title = ctk.CTkLabel(sidebar, text="OmniConvert", font=("Roboto", 24, "bold"), text_color=ACCENT_BLUE)
        title.pack(pady=(30, 40), padx=20, anchor="w")

        self.nav_buttons["image"] = self.create_nav_button(sidebar, "🖼️ Image Converter", lambda: self.switch_mode("image"), active=True)
        self.nav_buttons["video"] = self.create_nav_button(sidebar, "🎬 Video Converter", lambda: self.switch_mode("video"))
        self.nav_buttons["history"] = self.create_nav_button(sidebar, "🕒 History", lambda: self.switch_mode("history"))

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(expand=True, fill="both")
        self.create_nav_button(sidebar, "⚙️ Settings", lambda: self.open_settings_island(force=False)).pack(pady=(0, 20))

    def create_nav_button(self, parent, text, command, active=False):
        btn = ctk.CTkButton(
            parent, text=text, anchor="w", font=("Roboto", 14),
            fg_color="#1f2335" if active else "transparent",
            hover_color="#1f2335",
            text_color="white" if active else TEXT_MUTED,
            height=40, command=command
        )
        btn.pack(fill="x", padx=15, pady=5)
        return btn

    def switch_mode(self, mode):
        for name, btn in self.nav_buttons.items():
            if name == mode:
                btn.configure(fg_color="#1f2335", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)

        self.current_mode = mode

        if mode in ["image", "video"]:
            self.history_frame.grid_remove()
            self.converter_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
            
            if mode == "image":
                self.header_label.configure(text="Convert Images")
                self.supported_label.configure(text="PNG, JPG, WEBP, GIF supported")
            elif mode == "video":
                self.header_label.configure(text="Convert Videos")
                self.supported_label.configure(text="MP4, MKV, MP3, WAV supported")
            
            self.input_filepath = ""
            self.file_label.configure(text="No file selected")
            self.combo_from.configure(state="normal")
            self.combo_from.set("...")
            self.combo_from.configure(state="disabled")
            self.combo_to.configure(values=["..."])
            self.combo_to.set("...")

        elif mode == "history":
            self.converter_frame.grid_remove()
            self.history_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
            self.refresh_history_ui()

    # ==========================================
    # 2. UI: MAIN AREA (CONVERTER & HISTORY)
    # ==========================================
    def build_main_area(self):
        self.converter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.converter_frame.grid(row=0, column=1, sticky="nsew", padx=40, pady=40)
        self.converter_frame.grid_columnconfigure(0, weight=1)

        self.header_label = ctk.CTkLabel(self.converter_frame, text="Convert Images", font=("Roboto", 32, "bold"))
        self.header_label.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self.converter_frame, text="Select your files to instantly convert them to any format.", font=("Roboto", 14), text_color=TEXT_MUTED).grid(row=1, column=0, sticky="w", pady=(5, 30))

        drop_zone = ctk.CTkFrame(self.converter_frame, fg_color=BG_CARD, corner_radius=20, border_width=2, border_color="#272b40")
        drop_zone.grid(row=2, column=0, sticky="nsew", ipady=60)
        drop_zone.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(drop_zone, text="☁️", font=("Roboto", 48)).pack(pady=(40, 10))
        ctk.CTkLabel(drop_zone, text="Click to browse your computer", font=("Roboto", 18, "bold")).pack()
        self.supported_label = ctk.CTkLabel(drop_zone, text="PNG, JPG, WEBP, GIF supported", font=("Roboto", 12), text_color=TEXT_MUTED)
        self.supported_label.pack(pady=(5, 20))
        
        self.browse_btn = ctk.CTkButton(drop_zone, text="Choose Files", font=("Roboto", 14), fg_color="#2a2e42", hover_color="#363b52", command=self.browse_file)
        self.browse_btn.pack(pady=(0, 40))
        self.file_label = ctk.CTkLabel(drop_zone, text="No file selected", font=("Roboto", 12), text_color=ACCENT_BLUE)
        self.file_label.pack()

        controls_panel = ctk.CTkFrame(self.converter_frame, fg_color=BG_CARD, corner_radius=15)
        controls_panel.grid(row=3, column=0, sticky="ew", pady=30)
        controls_panel.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(controls_panel, text="CONVERT FROM", font=("Roboto", 10, "bold"), text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 0))
        self.combo_from = ctk.CTkComboBox(controls_panel, values=["..."], fg_color="#141622", border_color="#272b40", state="disabled")
        self.combo_from.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 20))

        ctk.CTkLabel(controls_panel, text="➔", font=("Roboto", 20)).grid(row=1, column=1)

        ctk.CTkLabel(controls_panel, text="CONVERT TO", font=("Roboto", 10, "bold"), text_color=TEXT_MUTED).grid(row=0, column=2, sticky="w", padx=20, pady=(15, 0))
        self.combo_to = ctk.CTkComboBox(controls_panel, values=["..."], fg_color="#141622", border_color="#272b40")
        self.combo_to.grid(row=1, column=2, sticky="ew", padx=20, pady=(5, 20))

        self.convert_btn = ctk.CTkButton(controls_panel, text="Convert Now", font=("Roboto", 14, "bold"), fg_color=ACCENT_PURPLE, hover_color="#7c3aed", height=40, command=self.start_conversion)
        self.convert_btn.grid(row=1, column=3, padx=20, pady=(5, 20))

        self.history_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.history_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.history_frame, text="Conversion History", font=("Roboto", 32, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self.history_frame, text="A log of your past file conversions.", font=("Roboto", 14), text_color=TEXT_MUTED).grid(row=1, column=0, sticky="w", pady=(5, 20))
        
        self.history_list = ctk.CTkScrollableFrame(self.history_frame, fg_color=BG_CARD, corner_radius=15, border_width=1, border_color="#272b40")
        self.history_list.grid(row=2, column=0, sticky="nsew")

    def refresh_history_ui(self):
        for widget in self.history_list.winfo_children():
            widget.destroy()

        if not self.history_logs:
            ctk.CTkLabel(self.history_list, text="No conversions yet.", text_color=TEXT_MUTED).pack(pady=40)
            return

        for log in reversed(self.history_logs):
            item_card = ctk.CTkFrame(self.history_list, fg_color="#1f2335", corner_radius=8)
            item_card.pack(fill="x", padx=10, pady=5)
            
            icon = "✅" if log['success'] else "❌"
            color = "#10b981" if log['success'] else "#ef4444"
            
            ctk.CTkLabel(item_card, text=f"{icon} {log['file']}", font=("Roboto", 14, "bold")).pack(side="left", padx=15, pady=15)
            ctk.CTkLabel(item_card, text=log['time'], text_color=TEXT_MUTED).pack(side="right", padx=15)
            ctk.CTkLabel(item_card, text="Success" if log['success'] else "Failed", text_color=color).pack(side="right", padx=15)

    # ==========================================
    # 3. UI: RIGHT SIDEBAR & SETTINGS
    # ==========================================
    def build_right_sidebar(self):
        self.queue_sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0)
        self.queue_sidebar.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(self.queue_sidebar, text="System Status", font=("Roboto", 16, "bold")).pack(pady=(30, 20), padx=20, anchor="w")

        self.status_card = ctk.CTkFrame(self.queue_sidebar, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=ACCENT_BLUE)
        self.status_card.pack(fill="x", padx=15, pady=5)
        self.status_title = ctk.CTkLabel(self.status_card, text="Waiting for file...", font=("Roboto", 12, "bold"))
        self.status_title.pack(anchor="w", padx=10, pady=(10, 10))

    def check_first_boot(self):
        if not self.output_directory:
            self.open_settings_island(force=True)

    def open_settings_island(self, force=False):
        island = ctk.CTkToplevel(self)
        island.title("Settings")
        island.geometry("450x250")
        island.configure(fg_color=BG_MAIN)
        island.resizable(False, False)
        island.transient(self)
        island.grab_set()

        x = self.winfo_x() + (self.winfo_width() // 2) - (450 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (250 // 2)
        island.geometry(f"+{x}+{y}")

        # The Anti-Bypass Lock!
        def on_close():
            if force and not self.output_directory:
                messagebox.showwarning("Hold on!", "You MUST select an output folder before using the app.")
            else:
                island.destroy()
        island.protocol("WM_DELETE_WINDOW", on_close)

        card = ctk.CTkFrame(island, fg_color=BG_CARD, corner_radius=15, border_width=1, border_color=ACCENT_PURPLE)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="⚙️ Preferences", font=("Roboto", 18, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(card, text="Where should converted files be saved?", font=("Roboto", 12), text_color=TEXT_MUTED).pack()

        path_frame = ctk.CTkFrame(card, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=15)
        
        path_entry = ctk.CTkEntry(path_frame, fg_color="#141622", border_color="#272b40", text_color=TEXT_MUTED)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if self.output_directory:
            path_entry.insert(0, self.output_directory)

        def pick_folder():
            folder = filedialog.askdirectory()
            if folder:
                path_entry.delete(0, 'end')
                path_entry.insert(0, folder)
                self.output_directory = folder

        def save_and_close():
            if not self.output_directory:
                messagebox.showwarning("Hold on!", "Please select a folder first.")
                return
            self.save_memory() # Save to json
            island.destroy()

        ctk.CTkButton(path_frame, text="Browse", width=70, fg_color="#2a2e42", command=pick_folder).pack(side="right")
        ctk.CTkButton(card, text="Save & Close", fg_color=ACCENT_PURPLE, hover_color="#7c3aed", command=save_and_close).pack(pady=(10, 20))

    # ==========================================
    # 5. ENGINE LOGIC
    # ==========================================
    def browse_file(self):
        if self.current_mode == "image":
            file_types = [("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.gif;*.tiff;*.ico")]
        elif self.current_mode == "video":
            file_types = [("Media Files", "*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.mp3;*.wav;*.flac")]
        else:
            file_types = [("All Files", "*.*")]

        filepath = filedialog.askopenfilename(filetypes=file_types)
        if not filepath:
            return

        self.input_filepath = filepath
        filename = os.path.basename(filepath)
        display_name = filename if len(filename) < 25 else filename[:22] + "..."
        self.file_label.configure(text=f"Selected: {display_name}")

        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        self.combo_from.configure(state="normal")
        self.combo_from.set(ext)
        self.combo_from.configure(state="disabled")

        if ext in IMAGE_FORMATS:
            self.file_type = 'image'
            self.combo_to.configure(values=IMAGE_FORMATS)
            self.combo_to.set(".png" if ext != ".png" else ".jpg")
            self.status_title.configure(text="Ready to convert image.")
        elif ext in VIDEO_FORMATS:
            self.file_type = 'video'
            self.combo_to.configure(values=VIDEO_FORMATS)
            self.combo_to.set(".mp4" if ext != ".mp4" else ".mkv")
            self.status_title.configure(text="Ready to convert media.")

    def start_conversion(self):
        if not self.input_filepath or not self.file_type:
            messagebox.showwarning("Warning", "Please select a valid file first.")
            return

        target_ext = self.combo_to.get()
        
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.browse_btn.configure(state="disabled")
        self.status_card.configure(border_color=ACCENT_PURPLE)
        self.status_title.configure(text="Processing... Please wait.")

        threading.Thread(target=self.run_conversion, args=(target_ext,), daemon=True).start()

    def run_conversion(self, target_ext):
        input_path = self.input_filepath
        name, _ = os.path.splitext(os.path.basename(input_path))
        output_path = os.path.join(self.output_directory, f"{name}_converted{target_ext}")
        
        success = False
        error_msg = ""

        try:
            if self.file_type == 'image':
                img = Image.open(input_path)
                if target_ext in ['.jpg', '.jpeg'] and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(output_path)
                success = True

            elif self.file_type == 'video':
                if not os.path.isfile(FFMPEG_EXE):
                    raise FileNotFoundError(
                        "The bundled FFmpeg engine is missing. Rebuild the app "
                        "with bin/ffmpeg.exe included."
                    )
                (
                    ffmpeg
                    .input(input_path)
                    .output(output_path)
                    .overwrite_output()
                    .run(cmd=FFMPEG_EXE, quiet=True)
                )
                success = True
        except Exception as e:
            error_msg = str(e)

        self.after(100, self.finish_conversion, success, output_path, error_msg)

    def finish_conversion(self, success, output_path, error_msg):
        self.convert_btn.configure(state="normal", text="Convert Now")
        self.browse_btn.configure(state="normal")

        current_time = datetime.datetime.now().strftime("%I:%M %p")
        self.history_logs.append({
            "file": os.path.basename(output_path),
            "success": success,
            "time": current_time
        })
        self.save_memory() # Save instantly so history is never lost!

        if success:
            self.status_card.configure(border_color="#10b981") 
            self.status_title.configure(text=f"✓ Saved to {os.path.basename(self.output_directory)}")
        else:
            self.status_card.configure(border_color="#ef4444") 
            self.status_title.configure(text="Conversion Failed.")
            messagebox.showerror("Error", f"Failed:\n{error_msg}")

if __name__ == "__main__":
    app = OmniConvertDashboard()
    app.mainloop()
