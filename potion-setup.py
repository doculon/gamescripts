import tkinter as tk
from tkinter import messagebox, simpledialog
import pyautogui
import cv2
import numpy as np
import json
import os
import time
from PIL import Image, ImageTk

class VisualSetupTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Potion Manager Visual Setup")
        self.root.geometry("600x700")  # Made window larger
        self.root.minsize(500, 650)    # Set minimum size
        
        # Configuration storage
        self.config = {
            "slot_regions": [],
            "slot_progress_bars": [],  # Progress bars for each slot
            "health_bar_region": None,
            "mana_bar_region": None,
            "health_number_region": None,  # For OCR reading of health numbers
            "mana_number_region": None,    # For OCR reading of mana numbers
            "health_pixel_point": None,    # Single pixel for health detection
            "mana_pixel_point": None,      # Single pixel for mana detection
            "health_pixel_color": None,    # Color when health is full
            "mana_pixel_color": None,      # Color when mana is full
            "slot_size": {"width": 40, "height": 40},
            "bar_size": {"width": 200, "height": 20}
        }
        
        self.setup_mode = None
        self.click_overlay = None
        self.preview_images = []
        
        self.create_ui()
        
    def create_ui(self):
        """Create the main UI"""
        # Create main frame with scrollbar
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title = tk.Label(scrollable_frame, text="Potion Manager Setup Tool", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Instructions
        instructions = tk.Label(scrollable_frame, 
                               text="Click buttons below to mark positions on your screen",
                               font=("Arial", 10))
        instructions.pack(pady=5)
        
        # Info frame
        info_frame = tk.LabelFrame(self.root, text="How to Use", padx=10, pady=10)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = """1. Click on a button below to select what to capture
2. Draw a rectangle around the UI element by clicking and dragging
3. For potion slots: Include the progress bar underneath in your rectangle
4. The rectangle will be saved automatically when you release the mouse
5. Press ESC to cancel the current capture"""
        
        tk.Label(info_frame, text=info_text, justify="left", font=("Arial", 9)).pack(anchor="w")
        
        # Setup buttons frame
        setup_frame = tk.LabelFrame(self.root, text="Click to Mark Positions", padx=10, pady=10)
        setup_frame.pack(fill="x", padx=10, pady=5)
        
        # Potion slots
        tk.Label(setup_frame, text="Potion Slots:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        slots_frame = tk.Frame(setup_frame)
        slots_frame.pack(fill="x", pady=5)
        
        for i in range(5):
            btn = tk.Button(slots_frame, text=f"Slot {i+1}", width=8,
                           command=lambda x=i: self.start_position_capture("slot", x))
            btn.pack(side="left", padx=2)
        
        
        # Health and Mana bars
        tk.Label(setup_frame, text="Resource Bars:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        bars_frame = tk.Frame(setup_frame)
        bars_frame.pack(fill="x", pady=5)
        
        tk.Button(bars_frame, text="Health Bar", width=10,
                 command=lambda: self.start_position_capture("health")).pack(side="left", padx=2)
        tk.Button(bars_frame, text="Mana Bar", width=10,
                 command=lambda: self.start_position_capture("mana")).pack(side="left", padx=2)
        
        # Pixel Detection (Low CPU)
        tk.Label(setup_frame, text="Pixel Detection Points (Low CPU):", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        pixel_frame = tk.Frame(setup_frame)
        pixel_frame.pack(fill="x", pady=5)
        
        tk.Button(pixel_frame, text="Health Pixel", width=12,
                 command=lambda: self.start_position_capture("health_pixel"),
                 bg="darkgreen", fg="white").pack(side="left", padx=2)
        tk.Button(pixel_frame, text="Mana Pixel", width=12,
                 command=lambda: self.start_position_capture("mana_pixel"),
                 bg="darkblue", fg="white").pack(side="left", padx=2)
        
        # Health and Mana numbers (for OCR)
        tk.Label(setup_frame, text="Resource Numbers (for OCR - High CPU):", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        numbers_frame = tk.Frame(setup_frame)
        numbers_frame.pack(fill="x", pady=5)
        
        tk.Button(numbers_frame, text="Health Numbers", width=12,
                 command=lambda: self.start_position_capture("health_number")).pack(side="left", padx=2)
        tk.Button(numbers_frame, text="Mana Numbers", width=12,
                 command=lambda: self.start_position_capture("mana_number")).pack(side="left", padx=2)
        
        
        # Progress Bar Areas (for template matching)
        tk.Label(setup_frame, text="Progress Bar Areas (Empty State):", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        progress_frame = tk.Frame(setup_frame)
        progress_frame.pack(fill="x", pady=5)
        
        for i in range(5):
            btn = tk.Button(progress_frame, text=f"Slot {i+1} Progress", width=12,
                           command=lambda x=i: self.start_position_capture("progress", x),
                           bg="orange", fg="white")
            btn.pack(side="left", padx=2)
        
        # Potion Template Capture (Slot-based)
        tk.Label(setup_frame, text="Potion Template Capture (Slot-based):", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
        
        template_frame = tk.LabelFrame(setup_frame, text="Template Settings", padx=5, pady=5)
        template_frame.pack(fill="x", padx=10, pady=5)
        
        # Potion name input
        name_frame = tk.Frame(template_frame)
        name_frame.pack(fill="x", pady=2)
        tk.Label(name_frame, text="Potion Name:").pack(side="left", padx=5)
        self.potion_name_entry = tk.Entry(name_frame, width=20)
        self.potion_name_entry.pack(side="left", padx=5)
        self.potion_name_entry.insert(0, "healing_potion")
        
        # Potion type selection
        type_frame = tk.Frame(template_frame)
        type_frame.pack(fill="x", pady=2)
        tk.Label(type_frame, text="Type:").pack(side="left", padx=5)
        self.template_potion_type = tk.StringVar(value="health")
        tk.Radiobutton(type_frame, text="Health", variable=self.template_potion_type, 
                      value="health", fg="red").pack(side="left")
        tk.Radiobutton(type_frame, text="Mana", variable=self.template_potion_type, 
                      value="mana", fg="blue").pack(side="left")
        tk.Radiobutton(type_frame, text="Utility", variable=self.template_potion_type, 
                      value="utility", fg="green").pack(side="left")
        
        # State selection
        state_frame = tk.Frame(template_frame)
        state_frame.pack(fill="x", pady=2)
        tk.Label(state_frame, text="State:").pack(side="left", padx=5)
        self.template_state = tk.StringVar(value="full")
        tk.Radiobutton(state_frame, text="Full", variable=self.template_state, 
                      value="full", fg="green").pack(side="left")
        tk.Radiobutton(state_frame, text="Empty", variable=self.template_state, 
                      value="empty", fg="red").pack(side="left")
        
        # Slot capture buttons
        slots_frame = tk.Frame(template_frame)
        slots_frame.pack(fill="x", pady=5)
        tk.Label(slots_frame, text="Capture from slot:").pack(side="left", padx=5)
        for i in range(5):
            tk.Button(slots_frame, text=f"Slot {i+1}", width=7,
                     command=lambda x=i: self.capture_slot_template(x),
                     bg="purple", fg="white").pack(side="left", padx=2)
        
        # Status frame
        status_frame = tk.LabelFrame(self.root, text="Current Configuration", padx=10, pady=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create scrollable text widget for status
        self.status_text = tk.Text(status_frame, height=10, width=50)
        scrollbar = tk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action buttons
        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(action_frame, text="Save Configuration", command=self.save_config,
                 bg="green", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(action_frame, text="Load Configuration", command=self.load_config,
                 bg="blue", fg="white").pack(side="left", padx=5)
        tk.Button(action_frame, text="Test Setup", command=self.test_setup,
                 bg="orange", fg="white").pack(side="left", padx=5)
        tk.Button(action_frame, text="Generate Code", command=self.generate_code,
                 bg="purple", fg="white").pack(side="left", padx=5)
        
        self.update_status_display()
    
    def start_position_capture(self, element_type, slot_index=None):
        """Start the position capture process"""
        self.setup_mode = (element_type, slot_index)
        
        # Hide main window
        self.root.withdraw()
        
        # Create click overlay
        self.create_click_overlay()
    
    def create_click_overlay(self):
        """Create transparent overlay for drawing rectangles"""
        self.click_overlay = tk.Toplevel()
        self.click_overlay.attributes("-fullscreen", True)
        
        element_type, slot_index = self.setup_mode
        if element_type in ["health_pixel", "mana_pixel"]:
            # For pixel capture, use very transparent overlay
            self.click_overlay.attributes("-alpha", 0.1)  # Almost invisible
            self.click_overlay.configure(bg='gray')
        else:
            # For rectangle drawing, use normal overlay
            self.click_overlay.attributes("-alpha", 0.3)
            self.click_overlay.configure(bg='red')
            
        self.click_overlay.attributes("-topmost", True)
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(self.click_overlay, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        if element_type in ["health_pixel", "mana_pixel"]:
            self.canvas.configure(bg='gray')
        else:
            self.canvas.configure(bg='red')
        
        # Instructions (element_type already extracted above)
        if element_type == "slot":
            instruction = f"Draw a rectangle around Potion Slot {slot_index + 1} (include progress bar underneath)"
        elif element_type == "health":
            instruction = "Draw a rectangle around your HEALTH BAR"
        elif element_type == "mana":
            instruction = "Draw a rectangle around your MANA BAR"
        elif element_type == "health_number":
            instruction = "Draw a rectangle around your HEALTH NUMBERS (e.g., 1500/1500)"
        elif element_type == "mana_number":
            instruction = "Draw a rectangle around your MANA NUMBERS (e.g., 1500/1500)"
        elif element_type == "health_pixel":
            instruction = "CLICK on a point in your health globe/bar that changes color when you lose health"
        elif element_type == "mana_pixel":
            instruction = "CLICK on a point in your mana globe/bar that changes color when you lose mana"
        elif element_type == "progress":
            instruction = f"Draw a rectangle around Slot {slot_index + 1}'s PROGRESS BAR area (when NO buff is active)"
        
        # Place instructions at top of screen
        self.canvas.create_text(self.click_overlay.winfo_screenwidth()//2, 50,
                               text=instruction, font=("Arial", 24, "bold"),
                               fill="white", tags="instruction")
        
        self.canvas.create_text(self.click_overlay.winfo_screenwidth()//2, 90,
                               text="Click and drag to draw rectangle - Press ESC to cancel",
                               font=("Arial", 16), fill="yellow", tags="instruction")
        
        # Variables for rectangle drawing
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # Bind mouse events
        element_type, _ = self.setup_mode
        if element_type in ["health_pixel", "mana_pixel"]:
            # For pixel detection, just capture single click
            self.canvas.bind("<Button-1>", self.on_pixel_click)
        else:
            # For rectangles, use drag behavior
            self.canvas.bind("<Button-1>", self.on_mouse_down)
            self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.click_overlay.bind("<KeyPress-Escape>", self.cancel_capture)
        self.click_overlay.focus_set()
    
    def on_mouse_down(self, event):
        """Handle mouse button down - start drawing rectangle"""
        self.start_x = event.x
        self.start_y = event.y
        
        # Remove any existing rectangle
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # Create new rectangle
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="lime", width=3, fill="", tags="selection"
        )
    
    def on_mouse_drag(self, event):
        """Handle mouse drag - update rectangle"""
        if self.rect_id and self.start_x is not None:
            # Update rectangle coordinates
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
    
    def on_mouse_release(self, event):
        """Handle mouse button release - finalize rectangle"""
        if self.start_x is None:
            return
        
        # Calculate the region (ensure positive width/height)
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        
        width = x2 - x1
        height = y2 - y1
        
        # Minimum size check
        if width < 5 or height < 5:
            messagebox.showwarning("Too Small", "Rectangle is too small. Please try again.")
            return
        
        # Convert canvas coordinates to screen coordinates
        x = self.click_overlay.winfo_x() + x1
        y = self.click_overlay.winfo_y() + y1
        
        # Store the region
        element_type, slot_index = self.setup_mode
        region = (x, y, width, height)
        
        if element_type == "slot":
            # Ensure we have enough slots in the list
            while len(self.config["slot_regions"]) <= slot_index:
                self.config["slot_regions"].append(None)
            self.config["slot_regions"][slot_index] = region
            
        elif element_type == "health":
            self.config["health_bar_region"] = region
            
        elif element_type == "mana":
            self.config["mana_bar_region"] = region
            
        elif element_type == "health_number":
            self.config["health_number_region"] = region
            
        elif element_type == "mana_number":
            self.config["mana_number_region"] = region
            
        elif element_type == "template":
            # Save the template image instead of storing region
            self.save_template(region)
        
        elif element_type == "progress":
            # Save progress bar template
            self.save_progress_template(region, slot_index)
        
        self.finish_capture()
    
    def on_pixel_click(self, event):
        """Handle single pixel click for health/mana detection"""
        x, y = event.x_root, event.y_root
        element_type, _ = self.setup_mode
        
        # Hide the overlay temporarily to get true colors
        self.click_overlay.withdraw()
        time.sleep(0.1)  # Brief pause to ensure overlay is hidden
        
        # Capture the pixel color at this position
        screenshot = pyautogui.screenshot()
        # Convert coordinates to screen coordinates
        pixel_color = screenshot.getpixel((x, y))
        
        # Show overlay again briefly
        self.click_overlay.deiconify()
        
        if element_type == "health_pixel":
            self.config["health_pixel_point"] = (x, y)
            self.config["health_pixel_color"] = pixel_color
            messagebox.showinfo("Pixel Captured", 
                              f"Health pixel captured at ({x}, {y})\n"
                              f"Color (RGB): {pixel_color}\n\n"
                              f"Make sure you have FULL HEALTH when capturing!")
        elif element_type == "mana_pixel":
            self.config["mana_pixel_point"] = (x, y)
            self.config["mana_pixel_color"] = pixel_color
            messagebox.showinfo("Pixel Captured", 
                              f"Mana pixel captured at ({x}, {y})\n"
                              f"Color (RGB): {pixel_color}\n\n"
                              f"Make sure you have FULL MANA when capturing!")
        
        self.finish_capture()
    
    def cancel_capture(self, event=None):
        """Cancel position capture"""
        self.finish_capture()
    
    def finish_capture(self):
        """Clean up after position capture"""
        if self.click_overlay:
            self.click_overlay.destroy()
            self.click_overlay = None
        
        self.root.deiconify()  # Show main window again
        self.update_status_display()
        self.setup_mode = None
    
    def update_status_display(self):
        """Update the status display"""
        self.status_text.delete(1.0, tk.END)
        
        # Slot regions
        self.status_text.insert(tk.END, "POTION SLOTS (including progress bars):\n")
        for i, region in enumerate(self.config["slot_regions"]):
            if region:
                self.status_text.insert(tk.END, f"  Slot {i+1}: {region}\n")
            else:
                self.status_text.insert(tk.END, f"  Slot {i+1}: Not set\n")
        
        # Resource bars
        self.status_text.insert(tk.END, "\nRESOURCE BARS:\n")
        if self.config["health_bar_region"]:
            self.status_text.insert(tk.END, f"  Health: {self.config['health_bar_region']}\n")
        else:
            self.status_text.insert(tk.END, "  Health: Not set\n")
            
        if self.config["mana_bar_region"]:
            self.status_text.insert(tk.END, f"  Mana: {self.config['mana_bar_region']}\n")
        else:
            self.status_text.insert(tk.END, "  Mana: Not set\n")
        
        # Pixel Detection
        self.status_text.insert(tk.END, "\nPIXEL DETECTION (Low CPU):\n")
        if self.config["health_pixel_point"]:
            self.status_text.insert(tk.END, f"  Health Pixel: {self.config['health_pixel_point']} ")
            if self.config["health_pixel_color"]:
                self.status_text.insert(tk.END, f"Color: RGB{self.config['health_pixel_color']}\n")
            else:
                self.status_text.insert(tk.END, "\n")
        else:
            self.status_text.insert(tk.END, "  Health Pixel: Not set\n")
            
        if self.config["mana_pixel_point"]:
            self.status_text.insert(tk.END, f"  Mana Pixel: {self.config['mana_pixel_point']} ")
            if self.config["mana_pixel_color"]:
                self.status_text.insert(tk.END, f"Color: RGB{self.config['mana_pixel_color']}\n")
            else:
                self.status_text.insert(tk.END, "\n")
        else:
            self.status_text.insert(tk.END, "  Mana Pixel: Not set\n")
        
        # Resource numbers
        self.status_text.insert(tk.END, "\nRESOURCE NUMBERS (OCR - High CPU):\n")
        if self.config["health_number_region"]:
            self.status_text.insert(tk.END, f"  Health Numbers: {self.config['health_number_region']}\n")
        else:
            self.status_text.insert(tk.END, "  Health Numbers: Not set\n")
            
        if self.config["mana_number_region"]:
            self.status_text.insert(tk.END, f"  Mana Numbers: {self.config['mana_number_region']}\n")
        else:
            self.status_text.insert(tk.END, "  Mana Numbers: Not set\n")
        
        # Progress bar regions
        self.status_text.insert(tk.END, "\nPROGRESS BAR AREAS:\n")
        for i, region in enumerate(self.config["slot_progress_bars"]):
            if region:
                self.status_text.insert(tk.END, f"  Slot {i+1}: {region}\n")
            else:
                self.status_text.insert(tk.END, f"  Slot {i+1}: Not set\n")
        
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Get current working directory
            current_dir = os.getcwd()
            print(f"Current directory: {current_dir}")
            
            # Create settings directory if it doesn't exist
            settings_dir = "settings"
            settings_path = os.path.join(current_dir, settings_dir)
            print(f"Creating settings directory at: {settings_path}")
            os.makedirs(settings_path, exist_ok=True)
            
            # Save to settings folder
            config_path = os.path.join(settings_dir, "potion_manager_config.json")
            full_path = os.path.abspath(config_path)
            print(f"Saving config to: {full_path}")
            
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            
            # Verify file was created
            if os.path.exists(config_path):
                print(f"Config file successfully created at: {full_path}")
                messagebox.showinfo("Success", f"Configuration saved to:\n{full_path}")
            else:
                print("WARNING: File was not created!")
                messagebox.showwarning("Warning", "File may not have been saved properly")
                
        except Exception as e:
            print(f"Error saving config: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            # Try loading from settings folder first
            config_path = os.path.join("settings", "potion_manager_config.json")
            if not os.path.exists(config_path):
                # Try old location for backward compatibility
                config_path = "potion_manager_config.json"
            
            with open(config_path, "r") as f:
                self.config = json.load(f)
            self.update_status_display()
            messagebox.showinfo("Success", f"Configuration loaded from {config_path}")
        except FileNotFoundError:
            messagebox.showwarning("Warning", "No configuration file found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def test_setup(self):
        """Test the current setup by taking screenshots"""
        try:
            test_dir = os.path.join("settings", "setup_test_screenshots")
            os.makedirs(test_dir, exist_ok=True)
            
            # Test slot regions
            for i, region in enumerate(self.config["slot_regions"]):
                if region:
                    screenshot = pyautogui.screenshot(region=region)
                    screenshot.save(f"{test_dir}/slot_{i+1}.png")
            
            # Test resource bars
            if self.config["health_bar_region"]:
                screenshot = pyautogui.screenshot(region=self.config["health_bar_region"])
                screenshot.save(f"{test_dir}/health_bar.png")
            
            if self.config["mana_bar_region"]:
                screenshot = pyautogui.screenshot(region=self.config["mana_bar_region"])
                screenshot.save(f"{test_dir}/mana_bar.png")
            
            if self.config["health_number_region"]:
                screenshot = pyautogui.screenshot(region=self.config["health_number_region"])
                screenshot.save(f"{test_dir}/health_numbers.png")
            
            if self.config["mana_number_region"]:
                screenshot = pyautogui.screenshot(region=self.config["mana_number_region"])
                screenshot.save(f"{test_dir}/mana_numbers.png")
            
            
            messagebox.showinfo("Test Complete", f"Test screenshots saved to {test_dir}/")
            
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
    
    def generate_code(self):
        """Generate Python code with current configuration"""
        code = f'''# Generated Potion Manager Configuration
# Copy this into your main potion manager script

def configure_potion_manager(manager):
    """Apply the visual setup configuration"""
    
    # Potion slot regions (includes progress bar area for each slot)
    manager.slot_regions = {self.config["slot_regions"]}
    
    # Resource bar regions
    manager.health_bar_region = {self.config["health_bar_region"]}
    manager.mana_bar_region = {self.config["mana_bar_region"]}
    
    # OCR number regions
    manager.health_number_region = {self.config["health_number_region"]}
    manager.mana_number_region = {self.config["mana_number_region"]}
    
    print("Configuration applied successfully!")
    print("Note: Potion slot regions include the progress bar area underneath each slot")

# Usage in your main script:
# manager = AdvancedPotionManager()
# configure_potion_manager(manager)
# manager.start()
'''
        
        # Save to file
        with open("potion_manager_setup.py", "w") as f:
            f.write(code)
        
        # Show in popup
        code_window = tk.Toplevel(self.root)
        code_window.title("Generated Configuration Code")
        code_window.geometry("600x400")
        
        text_widget = tk.Text(code_window, wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        text_widget.insert(1.0, code)
        
        tk.Label(code_window, text="Code saved to: potion_manager_setup.py", 
                font=("Arial", 10, "bold")).pack(pady=5)
    
    def capture_slot_template(self, slot_index):
        """Capture template from a specific slot"""
        # Check if slot region is configured
        if slot_index >= len(self.config["slot_regions"]) or not self.config["slot_regions"][slot_index]:
            messagebox.showerror("Error", f"Slot {slot_index + 1} position not configured!\nPlease configure slot positions first.")
            return
        
        # Get potion name
        potion_name = self.potion_name_entry.get().strip()
        if not potion_name:
            messagebox.showerror("Error", "Please enter a potion name!")
            return
        
        # Sanitize potion name for filename - replace spaces with hyphens
        potion_name = potion_name.replace(" ", "-").lower()
        
        # Get settings
        potion_type = self.template_potion_type.get()
        state = self.template_state.get()
        slot_num = slot_index + 1
        
        try:
            # Create directory structure
            folder_path = os.path.join(state, f"slot{slot_num}")
            os.makedirs(folder_path, exist_ok=True)
            
            # Get slot region
            region = self.config["slot_regions"][slot_index]
            
            # Capture the slot image
            screenshot = pyautogui.screenshot(region=region)
            
            # Save with descriptive filename
            filename = f"{potion_name}_{potion_type}.png"
            filepath = os.path.join(folder_path, filename)
            
            screenshot.save(filepath)
            
            messagebox.showinfo("Success", 
                              f"Template captured successfully!\n\n"
                              f"Slot: {slot_num}\n"
                              f"Name: {potion_name}\n"
                              f"Type: {potion_type}\n"
                              f"State: {state}\n"
                              f"Saved to: {filepath}")
            
            print(f"Captured template: {filepath}")
            
            # Clear the name field for next capture
            self.potion_name_entry.delete(0, tk.END)
            self.potion_name_entry.insert(0, "")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture template: {e}")
            print(f"Error capturing template: {e}")
    
    def save_progress_template(self, region, slot_index):
        """Save progress bar template for a specific slot"""
        try:
            # Create directory for progress bar templates
            progress_dir = os.path.join("settings", "progress_bars")
            os.makedirs(progress_dir, exist_ok=True)
            
            # Hide the overlay temporarily to get true colors
            if self.click_overlay:
                self.click_overlay.withdraw()
                time.sleep(0.1)  # Brief pause to ensure overlay is hidden
            
            # Capture the region
            screenshot = pyautogui.screenshot(region=region)
            
            # Show overlay again
            if self.click_overlay:
                self.click_overlay.deiconify()
            
            # Save as empty progress bar template
            filename = f"slot{slot_index + 1}_empty.png"
            filepath = os.path.join(progress_dir, filename)
            screenshot.save(filepath)
            
            # Store region in config
            while len(self.config["slot_progress_bars"]) <= slot_index:
                self.config["slot_progress_bars"].append(None)
            self.config["slot_progress_bars"][slot_index] = region
            
            messagebox.showinfo("Success", 
                              f"Progress bar template saved!\n\n"
                              f"Slot: {slot_index + 1}\n"
                              f"Saved to: {filepath}\n\n"
                              f"Make sure NO BUFF is active when capturing!")
            
            print(f"Saved progress bar template: {filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save progress template: {e}")
            print(f"Error saving progress template: {e}")
    
    def run(self):
        """Start the setup tool"""
        self.root.mainloop()

def main():
    """Run the visual setup tool"""
    print("Starting Visual Potion Manager Setup Tool...")
    tool = VisualSetupTool()
    tool.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")