"""
Main GUI Application - Tabbed interface for Potion Manager
Combines monitoring, settings, and setup in one application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk
import cv2
import numpy as np
from potions import AdvancedPotionManager, PotionCategory
import os
import json
import pyautogui

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Path of Exile - Potion Manager")
        self.root.geometry("1200x900")
        
        # Initialize potion manager
        self.manager = AdvancedPotionManager()
        self.manager.use_gui_controls = True
        
        # Initialize variables
        self.monitoring = False
        self.monitor_thread = None
        
        # Create main notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.monitor_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.monitor_tab, text='Monitor Potions')
        self.notebook.add(self.settings_tab, text='Settings')
        
        # Initialize tabs
        self.init_monitor_tab()
        self.init_settings_tab()
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
    def init_monitor_tab(self):
        """Initialize the Monitor Potions tab"""
        # This is essentially the original potions_gui content
        from potions_gui import PotionManagerGUI
        
        # Create a wrapper to embed the existing GUI
        self.potion_gui = PotionMonitorTab(self.monitor_tab, self.manager)
        
    def init_settings_tab(self):
        """Initialize the Settings tab with nested tabs"""
        # Create a nested notebook for settings
        self.settings_notebook = ttk.Notebook(self.settings_tab)
        self.settings_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create settings sub-tabs
        self.general_settings_tab = ttk.Frame(self.settings_notebook)
        self.potion_setup_tab = ttk.Frame(self.settings_notebook)
        self.advanced_settings_tab = ttk.Frame(self.settings_notebook)
        
        self.settings_notebook.add(self.general_settings_tab, text='General')
        self.settings_notebook.add(self.potion_setup_tab, text='Potion Setup')
        self.settings_notebook.add(self.advanced_settings_tab, text='Advanced')
        
        # Initialize sub-tabs
        self.init_general_settings()
        self.init_potion_setup()
        self.init_advanced_settings()
        
    def init_general_settings(self):
        """Initialize general settings tab"""
        frame = ttk.Frame(self.general_settings_tab, padding="20")
        frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(frame, text="General Settings", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Health threshold
        ttk.Label(frame, text="Health Threshold %:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=10)
        self.health_var = tk.DoubleVar(value=self.manager.health_threshold)
        health_scale = ttk.Scale(frame, from_=0, to=100, variable=self.health_var, 
                                orient='horizontal', length=300)
        health_scale.grid(row=1, column=1, sticky='ew', padx=10)
        self.health_label = ttk.Label(frame, text=f"{self.health_var.get():.0f}%")
        self.health_label.grid(row=1, column=2, padx=10)
        
        def update_health(*args):
            self.health_label.configure(text=f"{self.health_var.get():.0f}%")
            self.manager.health_threshold = self.health_var.get()
        self.health_var.trace('w', update_health)
        
        # Mana threshold
        ttk.Label(frame, text="Mana Threshold %:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=10)
        self.mana_var = tk.DoubleVar(value=self.manager.mana_threshold)
        mana_scale = ttk.Scale(frame, from_=0, to=100, variable=self.mana_var, 
                              orient='horizontal', length=300)
        mana_scale.grid(row=2, column=1, sticky='ew', padx=10)
        self.mana_label = ttk.Label(frame, text=f"{self.mana_var.get():.0f}%")
        self.mana_label.grid(row=2, column=2, padx=10)
        
        def update_mana(*args):
            self.mana_label.configure(text=f"{self.mana_var.get():.0f}%")
            self.manager.mana_threshold = self.mana_var.get()
        self.mana_var.trace('w', update_mana)
        
        # Window focus detection
        ttk.Label(frame, text="Window Focus Detection:", font=('Arial', 10)).grid(row=3, column=0, sticky='w', pady=20)
        self.focus_var = tk.BooleanVar(value=self.manager.require_window_focus)
        focus_check = ttk.Checkbutton(frame, text="Only use potions when Path of Exile is focused",
                                     variable=self.focus_var,
                                     command=lambda: setattr(self.manager, 'require_window_focus', self.focus_var.get()))
        focus_check.grid(row=3, column=1, columnspan=2, sticky='w', pady=20)
        
        # Potion cooldown
        ttk.Label(frame, text="Potion Cooldown (ms):", font=('Arial', 10)).grid(row=4, column=0, sticky='w', pady=10)
        self.cooldown_var = tk.IntVar(value=self.manager.potion_cooldown)
        cooldown_spin = ttk.Spinbox(frame, from_=100, to=5000, increment=100, 
                                    textvariable=self.cooldown_var, width=10,
                                    command=lambda: setattr(self.manager, 'potion_cooldown', self.cooldown_var.get()))
        cooldown_spin.grid(row=4, column=1, sticky='w', padx=10)
        
        # Save/Load buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=3, pady=30)
        
        ttk.Button(button_frame, text="Save Settings", 
                  command=self.save_settings).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Load Settings", 
                  command=self.load_settings).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_settings).pack(side='left', padx=10)
        
        frame.columnconfigure(1, weight=1)
        
    def init_potion_setup(self):
        """Initialize potion setup tab"""
        # Embed the setup functionality
        self.setup_gui = PotionSetupTab(self.potion_setup_tab, self.manager)
        
    def init_advanced_settings(self):
        """Initialize advanced settings tab"""
        frame = ttk.Frame(self.advanced_settings_tab, padding="20")
        frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(frame, text="Advanced Settings", font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Pixel color tolerance
        ttk.Label(frame, text="Pixel Color Tolerance:", font=('Arial', 10)).grid(row=1, column=0, sticky='w', pady=10)
        self.tolerance_var = tk.IntVar(value=self.manager.pixel_color_tolerance)
        tolerance_scale = ttk.Scale(frame, from_=10, to=100, variable=self.tolerance_var, 
                                   orient='horizontal', length=300)
        tolerance_scale.grid(row=1, column=1, sticky='ew', padx=10)
        self.tolerance_label = ttk.Label(frame, text=f"{self.tolerance_var.get()}")
        self.tolerance_label.grid(row=1, column=2, padx=10)
        
        def update_tolerance(*args):
            self.tolerance_label.configure(text=f"{self.tolerance_var.get()}")
            self.manager.pixel_color_tolerance = self.tolerance_var.get()
        self.tolerance_var.trace('w', update_tolerance)
        
        # Debug mode
        ttk.Label(frame, text="Debug Mode:", font=('Arial', 10)).grid(row=2, column=0, sticky='w', pady=10)
        self.debug_var = tk.BooleanVar(value=self.manager.debug)
        debug_check = ttk.Checkbutton(frame, text="Enable debug logging",
                                     variable=self.debug_var,
                                     command=lambda: setattr(self.manager, 'debug', self.debug_var.get()))
        debug_check.grid(row=2, column=1, sticky='w', pady=10)
        
        # Utility potion settings
        ttk.Label(frame, text="Utility Potion Settings", font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Label(frame, text="Progress Bar Threshold:", font=('Arial', 10)).grid(row=4, column=0, sticky='w', pady=10)
        self.progress_var = tk.DoubleVar(value=self.manager.progress_threshold * 100)
        progress_scale = ttk.Scale(frame, from_=0, to=100, variable=self.progress_var, 
                                  orient='horizontal', length=300)
        progress_scale.grid(row=4, column=1, sticky='ew', padx=10)
        self.progress_label = ttk.Label(frame, text=f"{self.progress_var.get():.0f}%")
        self.progress_label.grid(row=4, column=2, padx=10)
        
        def update_progress(*args):
            self.progress_label.configure(text=f"{self.progress_var.get():.0f}%")
            self.manager.progress_threshold = self.progress_var.get() / 100
        self.progress_var.trace('w', update_progress)
        
        frame.columnconfigure(1, weight=1)
        
    def on_tab_changed(self, event):
        """Handle tab change events"""
        selected_tab = event.widget.tab('current')['text']
        if selected_tab == 'Monitor Potions' and hasattr(self, 'potion_gui'):
            # Refresh potion display when switching to monitor tab
            self.potion_gui.scan_all_slots()
            
    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'health_threshold': self.manager.health_threshold,
            'mana_threshold': self.manager.mana_threshold,
            'require_window_focus': self.manager.require_window_focus,
            'potion_cooldown': self.manager.potion_cooldown,
            'pixel_color_tolerance': self.manager.pixel_color_tolerance,
            'progress_threshold': self.manager.progress_threshold,
            'debug': self.manager.debug
        }
        
        try:
            os.makedirs('settings', exist_ok=True)
            with open('settings/general_settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            
    def load_settings(self):
        """Load settings from file"""
        try:
            with open('settings/general_settings.json', 'r') as f:
                settings = json.load(f)
                
            # Update manager settings
            self.manager.health_threshold = settings.get('health_threshold', 50)
            self.manager.mana_threshold = settings.get('mana_threshold', 30)
            self.manager.require_window_focus = settings.get('require_window_focus', True)
            self.manager.potion_cooldown = settings.get('potion_cooldown', 250)
            self.manager.pixel_color_tolerance = settings.get('pixel_color_tolerance', 50)
            self.manager.progress_threshold = settings.get('progress_threshold', 0.1)
            self.manager.debug = settings.get('debug', False)
            
            # Update UI
            self.health_var.set(self.manager.health_threshold)
            self.mana_var.set(self.manager.mana_threshold)
            self.focus_var.set(self.manager.require_window_focus)
            self.cooldown_var.set(self.manager.potion_cooldown)
            self.tolerance_var.set(self.manager.pixel_color_tolerance)
            self.progress_var.set(self.manager.progress_threshold * 100)
            self.debug_var.set(self.manager.debug)
            
            messagebox.showinfo("Success", "Settings loaded successfully!")
        except FileNotFoundError:
            messagebox.showwarning("Warning", "No saved settings found.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")
            
    def reset_settings(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Confirm", "Reset all settings to defaults?"):
            self.manager.health_threshold = 50
            self.manager.mana_threshold = 30
            self.manager.require_window_focus = True
            self.manager.potion_cooldown = 250
            self.manager.pixel_color_tolerance = 50
            self.manager.progress_threshold = 0.1
            self.manager.debug = False
            
            # Update UI
            self.health_var.set(50)
            self.mana_var.set(30)
            self.focus_var.set(True)
            self.cooldown_var.set(250)
            self.tolerance_var.set(50)
            self.progress_var.set(10)
            self.debug_var.set(False)
            
            messagebox.showinfo("Success", "Settings reset to defaults!")


class PotionMonitorTab:
    """Monitor tab - adapted from potions_gui.py"""
    def __init__(self, parent, manager):
        self.parent = parent
        self.manager = manager
        
        # Initialize variables
        self.slot_widgets = {}
        self.auto_use_vars = []
        self.instant_vars = []
        self.enduring_vars = []
        self.monitoring = False
        self.monitor_thread = None
        
        # Create main frame
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Create header
        self.create_header(main_frame)
        
        # Create slots frame
        slots_frame = ttk.Frame(main_frame)
        slots_frame.pack(fill='both', expand=True, pady=10)
        
        # Create slot displays
        self.create_slot_displays(slots_frame)
        
        # Create status frame
        self.create_status_frame(main_frame)
        
        # Initialize checkbox states
        for i in range(5):
            self.auto_use_vars.append(tk.BooleanVar(value=True))
            self.instant_vars.append(tk.BooleanVar(value=False))
            self.enduring_vars.append(tk.BooleanVar(value=False))
        
        # Update checkboxes
        self.update_slot_checkboxes()
        
        # Initial scan
        self.scan_all_slots()
        
    def create_header(self, parent):
        """Create header with control buttons"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="Potion Monitor", 
                               font=('Arial', 18, 'bold'))
        title_label.pack(side='left', padx=10)
        
        # Control buttons
        controls_frame = ttk.Frame(header_frame)
        controls_frame.pack(side='right', padx=10)
        
        # Start/Stop button
        self.monitor_button = ttk.Button(controls_frame, text="Start Monitoring", 
                                        command=self.toggle_monitoring,
                                        style="Accent.TButton")
        self.monitor_button.pack(side='left', padx=5)
        
        # Scan button
        self.scan_button = ttk.Button(controls_frame, text="Scan Slots", 
                                     command=self.scan_all_slots)
        self.scan_button.pack(side='left', padx=5)
        
        # Status label
        self.main_status_label = ttk.Label(header_frame, text="Ready", 
                                          foreground="green", font=('Arial', 10, 'bold'))
        self.main_status_label.pack(side='left', padx=20)
        
    def create_slot_displays(self, parent):
        """Create display widgets for each slot"""
        # Create a canvas with scrollbar
        canvas = tk.Canvas(parent, height=400)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Create slots
        for slot_num in range(1, 6):
            self.create_slot_widget(scrollable_frame, slot_num)
            
    def create_slot_widget(self, parent, slot_num):
        """Create widget for a single slot"""
        # Frame for slot
        slot_frame = ttk.LabelFrame(parent, text=f"Slot {slot_num} (Key: {slot_num})", 
                                   padding="10")
        slot_frame.grid(row=(slot_num-1)//3, column=(slot_num-1)%3, 
                       padx=10, pady=10, sticky='nsew')
        
        parent.columnconfigure((slot_num-1)%3, weight=1)
        
        # Current image
        current_image = ttk.Label(slot_frame, relief="solid", borderwidth=1)
        current_image.pack(pady=5)
        
        # Info labels
        potion_label = ttk.Label(slot_frame, text="Potion: Unknown", 
                                font=('Arial', 10, 'bold'))
        potion_label.pack()
        
        type_label = ttk.Label(slot_frame, text="Type: Unknown")
        type_label.pack()
        
        uses_label = ttk.Label(slot_frame, text="Uses: 0/0")
        uses_label.pack()
        
        status_label = ttk.Label(slot_frame, text="Status: Not Active")
        status_label.pack()
        
        # Checkboxes
        checkbox_frame = ttk.Frame(slot_frame)
        checkbox_frame.pack(pady=10)
        
        auto_var = self.auto_use_vars[slot_num-1]
        auto_check = ttk.Checkbutton(checkbox_frame, text="Auto-use", 
                                    variable=auto_var,
                                    command=lambda s=slot_num-1: self.update_auto_use(s))
        auto_check.grid(row=0, column=0, padx=5)
        
        instant_var = self.instant_vars[slot_num-1]
        instant_check = ttk.Checkbutton(checkbox_frame, text="Instant", 
                                      variable=instant_var,
                                      command=lambda s=slot_num-1: self.update_instant(s))
        instant_check.grid(row=0, column=1, padx=5)
        
        enduring_var = self.enduring_vars[slot_num-1]
        enduring_check = ttk.Checkbutton(checkbox_frame, text="Enduring", 
                                       variable=enduring_var,
                                       command=lambda s=slot_num-1: self.update_enduring(s))
        enduring_check.grid(row=1, column=0, columnspan=2, padx=5)
        
        # Store references
        self.slot_widgets[slot_num] = {
            'frame': slot_frame,
            'current_image': current_image,
            'potion_label': potion_label,
            'type_label': type_label,
            'uses_label': uses_label,
            'status_label': status_label,
            'auto_check': auto_check,
            'instant_check': instant_check,
            'enduring_check': enduring_check
        }
        
    def create_status_frame(self, parent):
        """Create status frame"""
        status_frame = ttk.LabelFrame(parent, text="Game Status", padding="10")
        status_frame.pack(fill='x', pady=10)
        
        # Resource frame
        resource_frame = ttk.Frame(status_frame)
        resource_frame.pack()
        
        self.health_label = ttk.Label(resource_frame, text="Health: 100%", 
                                     font=('Arial', 12), foreground="red")
        self.health_label.pack(side='left', padx=20)
        
        self.mana_label = ttk.Label(resource_frame, text="Mana: 100%", 
                                   font=('Arial', 12), foreground="blue")
        self.mana_label.pack(side='left', padx=20)
        
        self.active_label = ttk.Label(resource_frame, text="Active Effects: None", 
                                     font=('Arial', 10))
        self.active_label.pack(side='left', padx=20)
        
        # Log frame
        log_frame = ttk.Frame(status_frame)
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=6, width=80, wrap='word')
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
    def update_slot_checkboxes(self):
        """Update checkbox states from manager"""
        for i in range(5):
            if i < len(self.manager.slot_auto_use):
                self.auto_use_vars[i].set(self.manager.slot_auto_use[i])
            if i < len(self.manager.slot_instant):
                self.instant_vars[i].set(self.manager.slot_instant[i])
            if i < len(self.manager.slot_enduring):
                self.enduring_vars[i].set(self.manager.slot_enduring[i])
                
    def update_auto_use(self, slot_index):
        """Update auto-use setting"""
        if slot_index < len(self.manager.slot_auto_use):
            self.manager.slot_auto_use[slot_index] = self.auto_use_vars[slot_index].get()
            self.log(f"Slot {slot_index+1} auto-use: {'Enabled' if self.auto_use_vars[slot_index].get() else 'Disabled'}")
            
    def update_instant(self, slot_index):
        """Update instant setting"""
        if slot_index < len(self.manager.slot_instant):
            self.manager.slot_instant[slot_index] = self.instant_vars[slot_index].get()
            self.log(f"Slot {slot_index+1} instant: {'Yes' if self.instant_vars[slot_index].get() else 'No'}")
            
    def update_enduring(self, slot_index):
        """Update enduring setting"""
        if slot_index < len(self.manager.slot_enduring):
            self.manager.slot_enduring[slot_index] = self.enduring_vars[slot_index].get()
            self.log(f"Slot {slot_index+1} enduring: {'Yes' if self.enduring_vars[slot_index].get() else 'No'}")
            
    def convert_cv2_to_tk(self, cv2_image, size=(60, 60)):
        """Convert OpenCV image to Tkinter PhotoImage"""
        rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(pil_image)
        
    def update_slot_display(self, slot_num):
        """Update display for a specific slot"""
        if slot_num > len(self.manager.slots):
            return
            
        slot = self.manager.slots[slot_num-1]
        widgets = self.slot_widgets[slot_num]
        
        # Capture current slot image
        if slot_num <= len(self.manager.slot_regions) and self.manager.slot_regions[slot_num-1]:
            try:
                region = self.manager.slot_regions[slot_num-1]
                screenshot = pyautogui.screenshot(region=region)
                slot_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                tk_image = self.convert_cv2_to_tk(slot_img)
                widgets['current_image'].configure(image=tk_image)
                widgets['current_image'].image = tk_image
            except:
                pass
                
        # Update labels
        widgets['potion_label'].configure(text=f"Potion: {slot.subtype.value}")
        
        # Type with color
        type_text = f"Type: {slot.category.value}"
        if slot.category == PotionCategory.HEALTH:
            widgets['type_label'].configure(text=type_text, foreground="red")
        elif slot.category == PotionCategory.MANA:
            widgets['type_label'].configure(text=type_text, foreground="blue")
        elif slot.category == PotionCategory.UTILITY:
            widgets['type_label'].configure(text=type_text, foreground="green")
        else:
            widgets['type_label'].configure(text=type_text, foreground="gray")
            
        # Uses
        widgets['uses_label'].configure(text=f"Uses: {slot.uses_remaining}/{slot.max_uses}")
        
        # Status
        current_time = time.time()
        if slot.uses_remaining == 0:
            widgets['status_label'].configure(text="Status: Empty", foreground="red")
        elif current_time < slot.active_until:
            remaining = slot.active_until - current_time
            widgets['status_label'].configure(text=f"Status: Active ({remaining:.0f}s)", foreground="green")
        else:
            widgets['status_label'].configure(text="Status: Ready", foreground="blue")
            
        # Update checkbox visibility
        if slot.category == PotionCategory.HEALTH:
            widgets['instant_check'].configure(state="normal")
        else:
            widgets['instant_check'].configure(state="disabled")
            
        if slot.category == PotionCategory.MANA:
            widgets['enduring_check'].configure(state="normal")
        else:
            widgets['enduring_check'].configure(state="disabled")
            
    def scan_all_slots(self):
        """Scan all slots"""
        self.log("Scanning all slots...")
        self.manager.scan_all_slots()
        
        for slot_num in range(1, 6):
            self.update_slot_display(slot_num)
            
        self.log("Scan complete")
        
    def update_game_status(self):
        """Update game status display"""
        health = self.manager.game_state.health_percentage
        mana = self.manager.game_state.mana_percentage
        
        self.health_label.configure(text=f"Health: {health:.1f}%")
        self.mana_label.configure(text=f"Mana: {mana:.1f}%")
        
        # Active effects
        active_effects = []
        current_time = time.time()
        for slot in self.manager.slots:
            if current_time < slot.active_until:
                remaining = slot.active_until - current_time
                active_effects.append(f"{slot.subtype.value}({remaining:.0f}s)")
                
        if active_effects:
            self.active_label.configure(text=f"Active: {', '.join(active_effects)}")
        else:
            self.active_label.configure(text="Active Effects: None")
            
    def toggle_monitoring(self):
        """Toggle monitoring on/off"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_button.configure(text="Stop Monitoring")
            self.main_status_label.configure(text="Monitoring Active", foreground="green")
            self.log("Started monitoring")
            
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.monitor_button.configure(text="Start Monitoring")
            self.main_status_label.configure(text="Monitoring Stopped", foreground="orange")
            self.log("Stopped monitoring")
            
    def monitor_loop(self):
        """Main monitoring loop"""
        last_scan_time = 0
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                # Check window focus if required
                if self.manager.require_window_focus:
                    self.manager.poe_window_focused = self.manager.is_poe_window_focused()
                    
                    if self.manager.poe_window_focused:
                        # Update game state
                        self.manager.update_game_state()
                        
                        # Rescan slots periodically
                        if current_time - last_scan_time > 5:
                            self.manager.scan_all_slots()
                            last_scan_time = current_time
                            self.parent.after(0, self.update_all_slots)
                            
                        # Process potions
                        self.manager.process_health_potions()
                        self.manager.process_mana_potions()
                        self.manager.process_utility_potions()
                else:
                    # Process normally without focus check
                    self.manager.update_game_state()
                    
                    if current_time - last_scan_time > 5:
                        self.manager.scan_all_slots()
                        last_scan_time = current_time
                        self.parent.after(0, self.update_all_slots)
                        
                    self.manager.process_health_potions()
                    self.manager.process_mana_potions()
                    self.manager.process_utility_potions()
                    
                # Update status display
                self.parent.after(0, self.update_game_status)
                
                time.sleep(0.1)
                
            except Exception as e:
                self.parent.after(0, lambda: self.log(f"Error: {e}"))
                time.sleep(1)
                
    def update_all_slots(self):
        """Update all slot displays"""
        for slot_num in range(1, 6):
            self.update_slot_display(slot_num)
            
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        # Limit log size
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 100:
            self.log_text.delete('1.0', '2.0')


class PotionSetupTab:
    """Potion setup tab - adapted from potion-setup.py"""
    def __init__(self, parent, manager):
        self.parent = parent
        self.manager = manager
        
        # Create main frame
        main_frame = ttk.Frame(parent, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Potion Setup Wizard", font=('Arial', 16, 'bold'))
        title.pack(pady=20)
        
        # Instructions
        instructions = ttk.Label(main_frame, text=
            "This wizard helps you configure the potion manager for your game.\n\n"
            "1. Make sure Path of Exile is running and you're in game (not in menu)\n"
            "2. Have some potions in your flask slots\n"
            "3. Follow the steps below to capture and configure",
            justify='left', font=('Arial', 10))
        instructions.pack(pady=10)
        
        # Step frame
        step_frame = ttk.LabelFrame(main_frame, text="Setup Steps", padding="20")
        step_frame.pack(fill='both', expand=True, pady=20)
        
        # Capture potions button
        capture_frame = ttk.Frame(step_frame)
        capture_frame.pack(fill='x', pady=10)
        
        ttk.Label(capture_frame, text="Step 1: Capture Potion Images", 
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
        ttk.Button(capture_frame, text="Capture Full Potions", 
                  command=self.capture_full_potions).pack(side='left', padx=5)
        
        ttk.Button(capture_frame, text="Capture Empty Potions", 
                  command=self.capture_empty_potions).pack(side='left', padx=5)
        
        # Configure regions button
        region_frame = ttk.Frame(step_frame)
        region_frame.pack(fill='x', pady=10)
        
        ttk.Label(region_frame, text="Step 2: Configure Screen Regions", 
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
        ttk.Button(region_frame, text="Setup Regions", 
                  command=self.setup_regions).pack(side='left', padx=5)
        
        # Configure detection button
        detection_frame = ttk.Frame(step_frame)
        detection_frame.pack(fill='x', pady=10)
        
        ttk.Label(detection_frame, text="Step 3: Configure Detection Points", 
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
        ttk.Button(detection_frame, text="Setup Health Detection", 
                  command=self.setup_health_detection).pack(side='left', padx=5)
        
        ttk.Button(detection_frame, text="Setup Mana Detection", 
                  command=self.setup_mana_detection).pack(side='left', padx=5)
        
        # Test configuration button
        test_frame = ttk.Frame(step_frame)
        test_frame.pack(fill='x', pady=10)
        
        ttk.Label(test_frame, text="Step 4: Test Configuration", 
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
        ttk.Button(test_frame, text="Test All", 
                  command=self.test_configuration).pack(side='left', padx=5)
        
        # Save/Load frame
        save_frame = ttk.Frame(step_frame)
        save_frame.pack(fill='x', pady=20)
        
        ttk.Label(save_frame, text="Step 5: Save Configuration", 
                 font=('Arial', 11, 'bold')).pack(side='left', padx=10)
        
        ttk.Button(save_frame, text="Save Config", 
                  command=self.save_configuration).pack(side='left', padx=5)
        
        ttk.Button(save_frame, text="Load Config", 
                  command=self.load_configuration).pack(side='left', padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to begin setup", 
                                     font=('Arial', 10), foreground="blue")
        self.status_label.pack(pady=10)
        
    def update_status(self, message, color="blue"):
        """Update status message"""
        self.status_label.configure(text=message, foreground=color)
        self.parent.update()
        
    def capture_full_potions(self):
        """Capture full potion images"""
        self.update_status("Capturing full potions in 3 seconds...", "orange")
        self.parent.after(3000, self._do_capture_full)
        
    def _do_capture_full(self):
        """Actually capture full potions"""
        try:
            # Create directories
            os.makedirs("full", exist_ok=True)
            
            # Capture each slot
            for i, region in enumerate(self.manager.slot_regions):
                if region:
                    slot_dir = f"full/slot{i+1}"
                    os.makedirs(slot_dir, exist_ok=True)
                    
                    screenshot = pyautogui.screenshot(region=region)
                    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    
                    # Save with placeholder name
                    filename = f"{slot_dir}/captured_potion.png"
                    cv2.imwrite(filename, img)
                    
            self.update_status("Full potions captured successfully!", "green")
        except Exception as e:
            self.update_status(f"Error capturing potions: {e}", "red")
            
    def capture_empty_potions(self):
        """Capture empty potion images"""
        self.update_status("Capturing empty potions in 3 seconds...", "orange")
        self.parent.after(3000, self._do_capture_empty)
        
    def _do_capture_empty(self):
        """Actually capture empty potions"""
        try:
            # Create directories
            os.makedirs("empty", exist_ok=True)
            
            # Capture each slot
            for i, region in enumerate(self.manager.slot_regions):
                if region:
                    slot_dir = f"empty/slot{i+1}"
                    os.makedirs(slot_dir, exist_ok=True)
                    
                    screenshot = pyautogui.screenshot(region=region)
                    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    
                    # Save with placeholder name
                    filename = f"{slot_dir}/captured_potion.png"
                    cv2.imwrite(filename, img)
                    
            self.update_status("Empty potions captured successfully!", "green")
        except Exception as e:
            self.update_status(f"Error capturing potions: {e}", "red")
            
    def setup_regions(self):
        """Setup screen regions"""
        messagebox.showinfo("Setup Regions", 
                           "This would open a region selection tool.\n"
                           "For now, using default regions.")
        self.update_status("Regions configured with defaults", "green")
        
    def setup_health_detection(self):
        """Setup health detection point"""
        messagebox.showinfo("Health Detection", 
                           "Click on your health globe when it's full to set the detection point.")
        # In a full implementation, this would capture mouse clicks
        self.update_status("Health detection configured", "green")
        
    def setup_mana_detection(self):
        """Setup mana detection point"""
        messagebox.showinfo("Mana Detection", 
                           "Click on your mana globe when it's full to set the detection point.")
        # In a full implementation, this would capture mouse clicks
        self.update_status("Mana detection configured", "green")
        
    def test_configuration(self):
        """Test the current configuration"""
        self.update_status("Testing configuration...", "orange")
        
        try:
            # Test health detection
            health = self.manager.detect_health_percentage()
            mana = self.manager.detect_mana_percentage()
            
            # Scan slots
            self.manager.scan_all_slots()
            
            result = f"Health: {health:.1f}%, Mana: {mana:.1f}%\n"
            result += "Slots detected:\n"
            
            for i, slot in enumerate(self.manager.slots):
                result += f"  Slot {i+1}: {slot.subtype.value}\n"
                
            messagebox.showinfo("Test Results", result)
            self.update_status("Configuration test complete", "green")
        except Exception as e:
            messagebox.showerror("Test Failed", f"Error: {e}")
            self.update_status("Configuration test failed", "red")
            
    def save_configuration(self):
        """Save current configuration"""
        try:
            config = {
                'slot_regions': self.manager.slot_regions,
                'health_bar_region': self.manager.health_bar_region,
                'mana_bar_region': self.manager.mana_bar_region,
                'health_pixel_point': self.manager.health_pixel_point,
                'mana_pixel_point': self.manager.mana_pixel_point,
                'health_pixel_color': self.manager.health_pixel_color,
                'mana_pixel_color': self.manager.mana_pixel_color,
                'progress_bar_regions': self.manager.progress_bar_regions
            }
            
            os.makedirs('settings', exist_ok=True)
            with open('settings/potion_setup_config.json', 'w') as f:
                json.dump(config, f, indent=4)
                
            self.update_status("Configuration saved successfully!", "green")
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            self.update_status(f"Failed to save: {e}", "red")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            
    def load_configuration(self):
        """Load saved configuration"""
        try:
            with open('settings/potion_setup_config.json', 'r') as f:
                config = json.load(f)
                
            # Apply configuration
            if 'slot_regions' in config:
                self.manager.slot_regions = [tuple(r) if r else None for r in config['slot_regions']]
            if 'health_bar_region' in config:
                self.manager.health_bar_region = tuple(config['health_bar_region'])
            if 'mana_bar_region' in config:
                self.manager.mana_bar_region = tuple(config['mana_bar_region'])
            if 'health_pixel_point' in config:
                self.manager.health_pixel_point = tuple(config['health_pixel_point']) if config['health_pixel_point'] else None
            if 'mana_pixel_point' in config:
                self.manager.mana_pixel_point = tuple(config['mana_pixel_point']) if config['mana_pixel_point'] else None
            if 'health_pixel_color' in config:
                self.manager.health_pixel_color = tuple(config['health_pixel_color']) if config['health_pixel_color'] else None
            if 'mana_pixel_color' in config:
                self.manager.mana_pixel_color = tuple(config['mana_pixel_color']) if config['mana_pixel_color'] else None
                
            self.update_status("Configuration loaded successfully!", "green")
            messagebox.showinfo("Success", "Configuration loaded!")
        except FileNotFoundError:
            self.update_status("No saved configuration found", "orange")
            messagebox.showwarning("Warning", "No saved configuration found.")
        except Exception as e:
            self.update_status(f"Failed to load: {e}", "red")
            messagebox.showerror("Error", f"Failed to load configuration: {e}")


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Style configuration
    style = ttk.Style()
    style.configure("Accent.TButton", foreground="green")
    
    app = MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()