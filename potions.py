import cv2
import numpy as np
import pyautogui
import time
import threading
import os
import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum
import platform
import subprocess

# OCR functionality has been removed

class PotionCategory(Enum):
    HEALTH = "health"
    MANA = "mana"
    UTILITY = "utility"
    EMPTY = "empty"

class PotionSubtype(Enum):
    # Health subtypes
    SMALL_HEALTH_INSTANT = "small_health_instant"
    LARGE_HEALTH_INSTANT = "large_health_instant"
    HEALTH_OVERTIME = "health_overtime"
    REGENERATION = "regeneration"
    
    # Mana subtypes
    SMALL_MANA_INSTANT = "small_mana_instant"
    LARGE_MANA_INSTANT = "large_mana_instant"
    MANA_OVERTIME = "mana_overtime"
    CLARITY = "clarity"
    
    # Utility subtypes
    QUICKSILVER = "quicksilver"
    STRENGTH = "strength"
    DEFENSE = "defense"
    INVISIBILITY = "invisibility"
    FIRE_RESISTANCE = "fire_resistance"
    JADE = "jade"
    GRANITE = "granite"
    SILVER = "silver"
    
    EMPTY = "empty"

@dataclass
class PotionSlot:
    slot_number: int
    category: PotionCategory = PotionCategory.EMPTY
    subtype: PotionSubtype = PotionSubtype.EMPTY
    hotkey: str = ""
    uses_remaining: int = 0
    max_uses: int = 0
    cooldown: float = 0.0
    last_used: float = 0.0
    duration: float = 0.0
    active_until: float = 0.0
    confidence: float = 0.0  # Detection confidence

@dataclass
class ActiveEffect:
    subtype: PotionSubtype
    started_at: float
    expires_at: float
    progress_bar_region: tuple = None

@dataclass
class GameState:
    health_percentage: float = 100.0
    mana_percentage: float = 100.0
    health_current: Optional[int] = None
    health_max: Optional[int] = None
    mana_current: Optional[int] = None
    mana_max: Optional[int] = None
    active_effects: List[ActiveEffect] = field(default_factory=list)

class AdvancedPotionManager:
    # Make enums accessible for GUI
    PotionSubtype = PotionSubtype
    PotionCategory = PotionCategory
    
    def __init__(self):
        self.slots: List[PotionSlot] = []
        self.game_state = GameState()
        self.health_threshold = 50.0
        self.mana_threshold = 30.0
        self.running = False
        
        # GUI control settings
        self.use_gui_controls = False
        self.slot_auto_use = [True, True, True, True, True]  # Which slots to auto-use
        self.slot_instant = [False, False, False, False, False]  # Which slots are instant
        self.slot_enduring = [False, False, False, False, False]  # Which slots are enduring mana
        self.health_potion_delay = 2.0  # Default 2 second delay for health potions
        self.instant_potion_delay = 0.3  # 0.3 second delay for instant potions
        self.mana_potion_delay = 3.0  # Default 3 second delay for mana potions
        self.last_health_potion_time = 0  # Track last health potion use (shared cooldown)
        
        # Window focus detection
        self.require_window_focus = True  # Only watch potions when Path of Exile is focused
        self.poe_window_focused = False
        
        # Screen regions (adjust these for your game)
        self.health_bar_region = (100, 50, 200, 20)
        self.mana_bar_region = (100, 80, 200, 20)
        self.health_pixel_point = None   # For pixel detection
        self.mana_pixel_point = None     # For pixel detection
        self.health_pixel_color = None   # Full health color
        self.mana_pixel_color = None     # Full mana color
        self.pixel_color_tolerance = 50  # Color difference tolerance (increase if needed)
        
        # Potion slot regions (will be loaded from config if available)
        self.slot_regions = [
            (50, 200, 40, 40),   # Slot 1
            (100, 200, 40, 40),  # Slot 2
            (150, 200, 40, 40),  # Slot 3
            (200, 200, 40, 40),  # Slot 4
            (250, 200, 40, 40),  # Slot 5
        ]
        
        # Template storage
        self.full_templates = {}  # Full potion templates
        self.empty_templates = {} # Empty potion templates
        self.progress_bar_templates = {}  # Empty progress bar templates
        self.slot_progress_regions = []  # Progress bar regions for each slot
        
        # Potion configurations
        self.potion_configs = self.setup_potion_configs()
        
        # Initialize slots
        self.setup_slots()
        
        # Try to load configuration from setup tool
        self.load_setup_config()
        
        # Load templates
        self.load_all_templates()

    def setup_potion_configs(self) -> Dict[PotionSubtype, dict]:
        """Define configurations for each potion subtype"""
        return {
            # Health potions
            PotionSubtype.SMALL_HEALTH_INSTANT: {
                "category": PotionCategory.HEALTH,
                "cooldown": 1.0,
                "max_uses": 3,
                "instant": True
            },
            PotionSubtype.LARGE_HEALTH_INSTANT: {
                "category": PotionCategory.HEALTH,
                "cooldown": 2.0,
                "max_uses": 2,
                "instant": True
            },
            PotionSubtype.HEALTH_OVERTIME: {
                "category": PotionCategory.HEALTH,
                "cooldown": 5.0,
                "max_uses": 2,
                "duration": 15.0,
                "instant": False
            },
            PotionSubtype.REGENERATION: {
                "category": PotionCategory.HEALTH,
                "cooldown": 8.0,
                "max_uses": 1,
                "duration": 30.0,
                "instant": False
            },
            
            # Mana potions
            PotionSubtype.SMALL_MANA_INSTANT: {
                "category": PotionCategory.MANA,
                "cooldown": 1.0,
                "max_uses": 3,
                "instant": True
            },
            PotionSubtype.LARGE_MANA_INSTANT: {
                "category": PotionCategory.MANA,
                "cooldown": 2.0,
                "max_uses": 2,
                "instant": True
            },
            PotionSubtype.MANA_OVERTIME: {
                "category": PotionCategory.MANA,
                "cooldown": 5.0,
                "max_uses": 2,
                "duration": 20.0,
                "instant": False
            },
            PotionSubtype.CLARITY: {
                "category": PotionCategory.MANA,
                "cooldown": 10.0,
                "max_uses": 1,
                "duration": 45.0,
                "instant": False
            },
            
            # Utility potions
            PotionSubtype.QUICKSILVER: {
                "category": PotionCategory.UTILITY,
                "cooldown": 2.0,
                "max_uses": 3,
                "duration": 20.0,
                "instant": False
            },
            PotionSubtype.STRENGTH: {
                "category": PotionCategory.UTILITY,
                "cooldown": 3.0,
                "max_uses": 2,
                "duration": 30.0,
                "instant": False
            },
            PotionSubtype.DEFENSE: {
                "category": PotionCategory.UTILITY,
                "cooldown": 3.0,
                "max_uses": 2,
                "duration": 30.0,
                "instant": False
            },
            PotionSubtype.INVISIBILITY: {
                "category": PotionCategory.UTILITY,
                "cooldown": 5.0,
                "max_uses": 1,
                "duration": 15.0,
                "instant": False
            },
            PotionSubtype.FIRE_RESISTANCE: {
                "category": PotionCategory.UTILITY,
                "cooldown": 4.0,
                "max_uses": 2,
                "duration": 60.0,
                "instant": False
            },
            PotionSubtype.JADE: {
                "category": PotionCategory.UTILITY,
                "cooldown": 3.0,
                "max_uses": 3,
                "duration": 30.0,
                "instant": False
            },
            PotionSubtype.GRANITE: {
                "category": PotionCategory.UTILITY,
                "cooldown": 3.0,
                "max_uses": 3,
                "duration": 30.0,
                "instant": False
            },
            PotionSubtype.SILVER: {
                "category": PotionCategory.UTILITY,
                "cooldown": 2.0,
                "max_uses": 3,
                "duration": 20.0,
                "instant": False
            }
        }

    def setup_slots(self):
        """Initialize empty slots"""
        self.slots = [
            PotionSlot(slot_number=i+1, hotkey=str(i+1))
            for i in range(5)
        ]
    
    def load_setup_config(self):
        """Load configuration from the setup tool if available"""
        # Try loading from settings folder first
        config_file = os.path.join("settings", "potion_manager_config.json")
        if not os.path.exists(config_file):
            # Try old location for backward compatibility
            config_file = "potion_manager_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                
                # Load slot regions if available
                if "slot_regions" in config and config["slot_regions"]:
                    valid_regions = [r for r in config["slot_regions"] if r is not None]
                    if valid_regions:
                        self.slot_regions = valid_regions
                        print(f"Loaded {len(valid_regions)} slot regions from config")
                
                # Load health bar region
                if "health_bar_region" in config and config["health_bar_region"]:
                    self.health_bar_region = tuple(config["health_bar_region"])
                    print("Loaded health bar region from config")
                
                # Load mana bar region
                if "mana_bar_region" in config and config["mana_bar_region"]:
                    self.mana_bar_region = tuple(config["mana_bar_region"])
                    print("Loaded mana bar region from config")
                
                # Load pixel detection settings
                if "health_pixel_point" in config and config["health_pixel_point"]:
                    self.health_pixel_point = tuple(config["health_pixel_point"])
                    print("Loaded health pixel point from config")
                    
                if "health_pixel_color" in config and config["health_pixel_color"]:
                    self.health_pixel_color = tuple(config["health_pixel_color"])
                    print(f"Loaded health pixel color: RGB{self.health_pixel_color}")
                    
                if "mana_pixel_point" in config and config["mana_pixel_point"]:
                    self.mana_pixel_point = tuple(config["mana_pixel_point"])
                    print("Loaded mana pixel point from config")
                    
                if "mana_pixel_color" in config and config["mana_pixel_color"]:
                    self.mana_pixel_color = tuple(config["mana_pixel_color"])
                    print(f"Loaded mana pixel color: RGB{self.mana_pixel_color}")
                
                # Load progress bar regions
                if "slot_progress_bars" in config and config["slot_progress_bars"]:
                    valid_progress = [r for r in config["slot_progress_bars"] if r is not None]
                    if valid_progress:
                        self.slot_progress_regions = valid_progress
                        print(f"Loaded {len(valid_progress)} progress bar regions from config")
                        # Load progress bar templates
                        self.load_progress_templates()
                
                print("Configuration loaded successfully from setup tool")
            except Exception as e:
                print(f"Failed to load config from {config_file}: {e}")
        else:
            print(f"No config file found at {config_file}, using default regions")

    def load_progress_templates(self):
        """Load empty progress bar templates"""
        progress_dir = os.path.join("settings", "progress_bars")
        if not os.path.exists(progress_dir):
            print("No progress bar templates found")
            return
        
        for i in range(5):
            template_path = os.path.join(progress_dir, f"slot{i+1}_empty.png")
            if os.path.exists(template_path):
                template = cv2.imread(template_path)
                if template is not None:
                    self.progress_bar_templates[i] = template
                    print(f"Loaded progress bar template for slot {i+1}")
    
    def load_all_templates(self):
        """Load full and empty templates for all potion types"""
        # Load from slot-based structure (full/slot1/, empty/slot1/, etc.)
        for state in ["full", "empty"]:
            if not os.path.exists(state):
                continue
                
            # Check each slot directory
            for slot_num in range(1, 6):
                slot_dir = os.path.join(state, f"slot{slot_num}")
                if not os.path.exists(slot_dir):
                    continue
                    
                # Load templates from this slot
                for filename in os.listdir(slot_dir):
                    if not filename.endswith('.png'):
                        continue
                    
                    # Parse filename: potion-name_type.png
                    name_without_ext = filename[:-4]  # Remove .png
                    parts = name_without_ext.rsplit('_', 1)  # Split from the right
                    
                    if len(parts) == 2:
                        potion_name, potion_type = parts
                        # Convert hyphenated name back to display name
                        display_name = potion_name.replace('-', ' ')
                        
                        # Load the template
                        template_path = os.path.join(slot_dir, filename)
                        template = cv2.imread(template_path)
                        
                        if template is not None:
                            # For now, store with a simple key
                            # You might want to map this to PotionSubtype enum
                            template_key = f"{potion_name}_{potion_type}"
                            
                            if state == "full":
                                self.full_templates[template_key] = template
                            else:
                                self.empty_templates[template_key] = template
                            
                            print(f"Loaded {state} template: {display_name} ({potion_type}) from slot {slot_num}")
        
        print(f"Loaded {len(self.full_templates)} full templates")
        print(f"Loaded {len(self.empty_templates)} empty templates")

    def create_template_structure(self):
        """Create directory structure for organizing potion templates"""
        # Create slot-based directories
        for state in ["full", "empty"]:
            for slot_num in range(1, 6):
                slot_dir = os.path.join(state, f"slot{slot_num}")
                os.makedirs(slot_dir, exist_ok=True)
        
        print("Created template directories:")
        print("  full/slot1/ ... full/slot5/")
        print("  empty/slot1/ ... empty/slot5/")
        print("\nPlace your potion images in these folders based on:")
        print("  - State: full/ for potions with uses, empty/ for depleted potions")
        print("  - Slot: slot1/ through slot5/ for each potion slot")
        print("\nFilename format: {potion-name}_{type}.png")
        print("Example: quicksilver_utility.png, small-health-flask_health.png, etc.")

    def detect_potion_type_and_uses(self, slot_index: int) -> tuple:
        """Detect potion type and remaining uses - matching test_all_slots logic"""
        if slot_index >= len(self.slot_regions):
            return PotionSubtype.EMPTY, 0, 0.0
        
        region = self.slot_regions[slot_index]
        screenshot = pyautogui.screenshot(region=region)
        slot_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        best_match = PotionSubtype.EMPTY
        best_confidence = 0.0
        has_uses = False
        best_match_info = None
        best_match_name = None
        
        slot_num = slot_index + 1  # Convert 0-based to 1-based
        
        # Check templates for THIS SPECIFIC SLOT only (like test_all_slots does)
        for state in ['full', 'empty']:
            slot_dir = os.path.join(state, f'slot{slot_num}')
            if not os.path.exists(slot_dir):
                continue
                
            for filename in os.listdir(slot_dir):
                if not filename.endswith('.png'):
                    continue
                
                # Load template
                template_path = os.path.join(slot_dir, filename)
                template = cv2.imread(template_path)
                if template is None:
                    continue
                
                # Resize template if needed
                if template.shape[:2] != slot_img.shape[:2]:
                    template = cv2.resize(template, (slot_img.shape[1], slot_img.shape[0]))
                
                # Match template using TM_SQDIFF_NORMED (same as test_all_slots)
                result = cv2.matchTemplate(slot_img, template, cv2.TM_SQDIFF_NORMED)
                min_val, _, _, _ = cv2.minMaxLoc(result)
                
                # Convert to similarity score
                similarity = 1.0 - min_val
                
                # Higher threshold for empty templates to avoid false positives
                threshold = 0.98 if state == 'empty' else 0.8
                
                if similarity > best_confidence and similarity > threshold:
                    best_confidence = similarity
                    best_match_name = filename[:-4]  # Remove .png
                    has_uses = (state == 'full')
                    
                    # Parse filename
                    parts = best_match_name.rsplit('_', 1)
                    if len(parts) == 2:
                        best_match_info = {
                            'name': parts[0].replace('-', ' '),
                            'type': parts[1]
                        }
        
        # Try to map to PotionSubtype enum based on the detected info
        if best_match_info:
            # Map common potion names/types to PotionSubtype
            name_lower = best_match_info['name'].lower()
            type_lower = best_match_info['type'].lower()
            
            if 'quicksilver' in name_lower:
                best_match = PotionSubtype.QUICKSILVER
            elif 'silver' in name_lower and type_lower == 'utility':
                best_match = PotionSubtype.SILVER  # Silver flask is its own type
            elif 'health' in name_lower or type_lower == 'health':
                if 'small' in name_lower:
                    best_match = PotionSubtype.SMALL_HEALTH_INSTANT
                elif 'large' in name_lower:
                    best_match = PotionSubtype.LARGE_HEALTH_INSTANT
                else:
                    best_match = PotionSubtype.SMALL_HEALTH_INSTANT
            elif 'mana' in name_lower or type_lower == 'mana':
                if 'small' in name_lower:
                    best_match = PotionSubtype.SMALL_MANA_INSTANT
                elif 'large' in name_lower:
                    best_match = PotionSubtype.LARGE_MANA_INSTANT
                else:
                    best_match = PotionSubtype.SMALL_MANA_INSTANT
            elif 'defense' in name_lower:
                best_match = PotionSubtype.DEFENSE
            elif 'invisibility' in name_lower:
                best_match = PotionSubtype.INVISIBILITY
            elif 'fire' in name_lower and 'resistance' in name_lower:
                best_match = PotionSubtype.FIRE_RESISTANCE
            elif 'jade' in name_lower:
                best_match = PotionSubtype.JADE
            elif 'granite' in name_lower:
                best_match = PotionSubtype.GRANITE
            
            # Print detected info
            print(f"Slot {slot_index + 1}: Detected {best_match_info['name']} ({best_match_info['type']}) - Mapped to {best_match.value}")
        
        # Estimate uses remaining (you might need to adjust this logic)
        uses_remaining = 0
        if has_uses and best_match != PotionSubtype.EMPTY:
            config = self.potion_configs.get(best_match, {})
            max_uses = config.get("max_uses", 1)
            
            # Simple estimation - you could make this more sophisticated
            # by analyzing the potion's visual state more carefully
            uses_remaining = max_uses if has_uses else 0
        
        return best_match, uses_remaining, best_confidence

    def detect_slot_progress_bar(self, slot_index: int) -> bool:
        """Detect if a progress bar is active in a specific slot using template matching"""
        # First try template matching if available
        if slot_index in self.progress_bar_templates and slot_index < len(self.slot_progress_regions):
            progress_region = self.slot_progress_regions[slot_index]
            if progress_region:
                try:
                    # Capture current progress bar area
                    screenshot = pyautogui.screenshot(region=progress_region)
                    current_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    
                    # Get the empty template
                    empty_template = self.progress_bar_templates[slot_index]
                    
                    # Ensure sizes match
                    if current_img.shape[:2] == empty_template.shape[:2]:
                        # Compare with template
                        result = cv2.matchTemplate(current_img, empty_template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(result)
                        
                        # High match = empty (no progress bar), Low match = active progress bar
                        if max_val > 0.8:  # 80% match with empty template
                            return False  # No progress bar active
                        else:
                            return True   # Progress bar is active
                except Exception as e:
                    print(f"Error in template matching: {e}")
        
        # Fallback to color detection if template matching not available
        if slot_index >= len(self.slot_regions):
            return False
        
        region = self.slot_regions[slot_index]
        screenshot = pyautogui.screenshot(region=region)
        slot_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Extract the progress bar area (bottom portion of slot region)
        height = slot_img.shape[0]
        progress_start = int(height * 0.7)  # Bottom 30% for progress bar
        progress_bar_area = slot_img[progress_start:, :]
        
        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(progress_bar_area, cv2.COLOR_BGR2GRAY)
        
        # Look for horizontal lines that indicate a progress bar
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=20, maxLineGap=5)
        
        # Also check for colored pixels that might indicate a progress bar
        # Many games use bright colors for progress bars
        hsv = cv2.cvtColor(progress_bar_area, cv2.COLOR_BGR2HSV)
        
        # Define ranges for common progress bar colors (adjust based on your game)
        # Green progress bar
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Blue progress bar
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Yellow/Orange progress bar
        lower_yellow = np.array([20, 50, 50])
        upper_yellow = np.array([40, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Combine masks
        combined_mask = green_mask | blue_mask | yellow_mask
        
        # Count colored pixels
        colored_pixels = cv2.countNonZero(combined_mask)
        total_pixels = progress_bar_area.shape[0] * progress_bar_area.shape[1]
        
        # Progress bar is active if we detect lines or significant colored area
        has_lines = lines is not None and len(lines) > 0
        has_colored_bar = colored_pixels > (total_pixels * 0.1)  # At least 10% colored
        
        return has_lines or has_colored_bar
    
    def detect_active_utility_effects(self) -> List[ActiveEffect]:
        """Detect active utility potions by scanning progress bars in each slot"""
        active_effects = []
        current_time = time.time()
        
        # Check each slot for active progress bars
        for i, slot in enumerate(self.slots):
            # Only check utility potions
            if slot.category == PotionCategory.UTILITY and slot.subtype != PotionSubtype.EMPTY:
                if self.detect_slot_progress_bar(i):
                    # Progress bar detected, potion is active
                    if current_time < slot.active_until:
                        effect = ActiveEffect(
                            subtype=slot.subtype,
                            started_at=slot.last_used,
                            expires_at=slot.active_until,
                            progress_bar_region=self.slot_regions[i]
                        )
                        active_effects.append(effect)
        
        return active_effects

    def scan_all_slots(self):
        """Scan all slots and update their states"""
        print("Scanning potion slots...")
        
        for i, slot in enumerate(self.slots):
            subtype, uses, confidence = self.detect_potion_type_and_uses(i)
            
            # Update slot if changed
            if slot.subtype != subtype or slot.uses_remaining != uses:
                old_info = f"{slot.subtype.value}({slot.uses_remaining})"
                
                slot.subtype = subtype
                slot.uses_remaining = uses
                slot.confidence = confidence
                
                if subtype != PotionSubtype.EMPTY:
                    config = self.potion_configs[subtype]
                    slot.category = config["category"]
                    slot.cooldown = 0.0  # No cooldowns - just check empty/full
                    slot.max_uses = config["max_uses"]
                    slot.duration = config.get("duration", 0.0)
                else:
                    slot.category = PotionCategory.EMPTY
                    slot.cooldown = 0.0
                    slot.max_uses = 0
                    slot.duration = 0.0
                
                new_info = f"{slot.subtype.value}({slot.uses_remaining})"
                print(f"Slot {i+1}: {old_info} -> {new_info} (conf: {confidence:.2f})")

    def can_use_potion(self, slot: PotionSlot) -> bool:
        """Check if potion can be used - simplified to just check if not empty"""
        # Only check if the flask has uses (not empty)
        if slot.uses_remaining <= 0 or slot.category == PotionCategory.EMPTY:
            return False
        
        # For utility potions, check if there's already an active effect
        if slot.category == PotionCategory.UTILITY:
            return self.can_use_utility_potion(slot)
        
        return True

    def can_use_utility_potion(self, slot: PotionSlot) -> bool:
        """Check if utility potion can be used - only check if buff is active via progress bar"""
        # Check if this slot has an active progress bar
        slot_index = slot.slot_number - 1
        if self.detect_slot_progress_bar(slot_index):
            return False  # Progress bar active = buff is active, don't use
        
        return True

    def can_use_health_potion(self, slot: PotionSlot) -> bool:
        """Check if health potion can be used - always allow if not empty"""
        return True

    def can_use_mana_potion(self, slot: PotionSlot) -> bool:
        """Check if mana potion can be used - always allow if not empty"""
        return True

    def use_potion(self, slot: PotionSlot) -> bool:
        """Use a potion and update its state"""
        if not self.can_use_potion(slot):
            return False
        
        print(f"\n>>> USING POTION: {slot.subtype.value} (slot {slot.slot_number})")
        print(f"    Pressing key: {slot.hotkey}")
        print(f"    Uses remaining after use: {slot.uses_remaining-1}")
        
        # Press the hotkey
        pyautogui.press(slot.hotkey)
        
        current_time = time.time()
        slot.last_used = current_time
        slot.uses_remaining -= 1
        
        # Set active duration for non-instant potions
        config = self.potion_configs[slot.subtype]
        if not config.get("instant", True):
            slot.active_until = current_time + slot.duration
        
        return True

    def get_available_potions(self, category: PotionCategory) -> List[PotionSlot]:
        """Get all available potions of a specific category"""
        return [slot for slot in self.slots 
                if slot.category == category and slot.uses_remaining > 0]

    def should_use_health_potion(self) -> bool:
        """Check if we should use a health potion - use when health is not full"""
        available = self.get_available_potions(PotionCategory.HEALTH)
        # Use potion when health is below 100% (not full)
        return len(available) > 0 and self.game_state.health_percentage < 100.0

    def should_use_mana_potion(self) -> bool:
        """Check if we should use a mana potion - use when mana is not full"""
        available = self.get_available_potions(PotionCategory.MANA)
        # Use potion when mana is below 100% (not full)
        return len(available) > 0 and self.game_state.mana_percentage < 100.0

    def process_health_potions(self):
        """Use health potion if needed - with both shared and per-slot cooldown"""
        if not self.should_use_health_potion():
            return
        
        current_time = time.time()
        
        # Check shared health potion cooldown first
        time_since_last_health = current_time - self.last_health_potion_time
        min_shared_cooldown = self.instant_potion_delay  # At minimum, wait 300ms between any health potions
        
        if time_since_last_health < min_shared_cooldown:
            return  # Too soon after last health potion
        
        available = self.get_available_potions(PotionCategory.HEALTH)
        
        # Filter by GUI controls and check per-slot cooldown
        if self.use_gui_controls:
            usable = []
            for i, slot in enumerate(self.slots):
                if (i < len(self.slot_auto_use) and self.slot_auto_use[i] and
                    slot in available and self.can_use_potion(slot)):
                    
                    # Check per-slot cooldown
                    time_since_slot_used = current_time - slot.last_used
                    
                    # Determine cooldown based on instant setting
                    if i < len(self.slot_instant) and self.slot_instant[i]:
                        required_cooldown = self.instant_potion_delay  # 300ms for instant
                    else:
                        required_cooldown = self.health_potion_delay  # 2s for non-instant
                    
                    # Check both shared cooldown and per-slot cooldown
                    if (time_since_slot_used >= required_cooldown and 
                        time_since_last_health >= required_cooldown):
                        usable.append((i, slot))
        else:
            usable = []
            for i, slot in enumerate(self.slots):
                if slot in available and self.can_use_potion(slot):
                    # Check per-slot cooldown
                    time_since_slot_used = current_time - slot.last_used
                    if (time_since_slot_used >= self.health_potion_delay and
                        time_since_last_health >= self.health_potion_delay):
                        usable.append((i, slot))
        
        if usable:
            # Sort by uses remaining (use fuller potions first)
            usable.sort(key=lambda x: x[1].uses_remaining, reverse=True)
            slot_index, slot = usable[0]
            self.use_potion(slot)
            self.last_health_potion_time = current_time  # Update shared cooldown

    def process_mana_potions(self):
        """Use mana potion if needed - with per-slot cooldown for non-enduring, progress check for enduring"""
        if not self.should_use_mana_potion():
            return
        
        current_time = time.time()
        available = self.get_available_potions(PotionCategory.MANA)
        
        # Filter by GUI controls if enabled
        if self.use_gui_controls:
            usable = []
            for i, slot in enumerate(self.slots):
                if (i < len(self.slot_auto_use) and self.slot_auto_use[i] and
                    slot in available and self.can_use_potion(slot)):
                    
                    # Check if this is an enduring mana flask
                    is_enduring = i < len(self.slot_enduring) and self.slot_enduring[i]
                    
                    if is_enduring:
                        # For enduring flasks, check if buff is active via progress bar
                        if not self.detect_slot_progress_bar(i):
                            # No buff active, can use
                            usable.append((i, slot))
                    else:
                        # For non-enduring, check per-slot cooldown
                        time_since_last = current_time - slot.last_used
                        if time_since_last >= self.mana_potion_delay:
                            usable.append((i, slot))
        else:
            # Non-GUI mode - check per-slot cooldown
            usable = []
            for i, slot in enumerate(self.slots):
                if slot in available and self.can_use_potion(slot):
                    time_since_last = current_time - slot.last_used
                    if time_since_last >= self.mana_potion_delay:
                        usable.append((i, slot))
        
        if usable:
            # Sort by uses remaining (use fuller potions first)
            usable.sort(key=lambda x: x[1].uses_remaining, reverse=True)
            slot_index, slot = usable[0]
            self.use_potion(slot)
    
    def process_utility_potions(self):
        """Process utility potion usage - keep buffs active and alternate same types"""
        # Only print debug occasionally to avoid spam
        current_time = time.time()
        if not hasattr(self, '_last_utility_debug') or current_time - self._last_utility_debug > 2:
            self._last_utility_debug = current_time
            debug_enabled = True
        else:
            debug_enabled = False
            
        if debug_enabled:
            print("\n[DEBUG] Processing utility potions...")
        
        # First, check all utility slots for active effects (including empty ones)
        active_utility_types = set()
        for i, slot in enumerate(self.slots):
            if slot.category == PotionCategory.UTILITY and slot.subtype != PotionSubtype.EMPTY:
                # Check if this slot has an active progress bar
                if self.detect_slot_progress_bar(i):
                    active_utility_types.add(slot.subtype.value)
                    if debug_enabled:
                        print(f"  Slot {i+1}: {slot.subtype.value} is ACTIVE (progress bar detected)")
        
        # Group utility potions by name/type (only non-empty ones)
        utility_groups = {}
        
        for i, slot in enumerate(self.slots):
            if debug_enabled:
                print(f"  Checking slot {i+1}: {slot.subtype.value}, category={slot.category.value}, uses={slot.uses_remaining}")
            
            # Check GUI controls if enabled
            if self.use_gui_controls and (i >= len(self.slot_auto_use) or not self.slot_auto_use[i]):
                if debug_enabled:
                    print(f"    Skipped - auto-use disabled in GUI")
                continue  # Skip this slot if auto-use is disabled
                
            if (slot.category == PotionCategory.UTILITY and 
                slot.uses_remaining > 0 and
                slot.subtype != PotionSubtype.EMPTY):
                
                # Get the potion name from the subtype
                key = slot.subtype.value
                if key not in utility_groups:
                    utility_groups[key] = []
                utility_groups[key].append((i, slot))
                if debug_enabled:
                    print(f"    Added to utility group: {key}")
        
        # Process each group of utility potions
        print(f"\nUtility groups found: {list(utility_groups.keys())}")
        print(f"Active utility types: {active_utility_types}")
        
        for potion_type, slots_list in utility_groups.items():
            print(f"\n[DEBUG] Processing {potion_type} group with {len(slots_list)} slots")
            
            # Check if this type is already active (from our earlier check)
            if potion_type in active_utility_types:
                print(f"  {potion_type} is already active, skipping")
                continue
            
            # No active buff of this type, find an available slot to use
            print(f"\n[DEBUG] {potion_type}: No active buff detected, looking for available slot...")
            current_time = time.time()
            best_slot = None
            best_index = None
            
            for slot_index, slot in slots_list:
                # Check if this slot can be used
                can_use = self.can_use_potion(slot)
                print(f"  Slot {slot_index + 1}: can_use={can_use}, has_uses={slot.uses_remaining > 0}")
                if can_use:
                    # Just use the first available slot
                    best_slot = slot
                    best_index = slot_index
                    break
            
            # Use the best available slot
            if best_slot is not None:
                print(f"\nAuto-using utility potion: {best_slot.subtype.value} (slot {best_index + 1})")
                self.use_potion(best_slot)
            else:
                print(f"\n[DEBUG] No available slot for {potion_type} - all empty")

    def color_distance(self, color1: tuple, color2: tuple) -> float:
        """Calculate Euclidean distance between two RGB colors"""
        return ((color1[0] - color2[0])**2 + 
                (color1[1] - color2[1])**2 + 
                (color1[2] - color2[2])**2) ** 0.5
    
    def detect_health_percentage_pixel(self) -> float:
        """Detect health using pixel color comparison"""
        if not self.health_pixel_point or not self.health_pixel_color:
            return None
            
        try:
            # Get current pixel color
            screenshot = pyautogui.screenshot()
            current_color = screenshot.getpixel(self.health_pixel_point)
            
            # Calculate color distance from full health color
            distance = self.color_distance(current_color, self.health_pixel_color)
            
            # Binary detection: Full health or low health
            if distance < self.pixel_color_tolerance:
                return 100.0  # Full health - no potion needed
            else:
                # Color changed = health is not full, trigger potion use
                return 40.0  # Return low value to trigger potion if below threshold
                
        except Exception as e:
            print(f"Pixel detection error: {e}")
            return None
    
    def detect_mana_percentage_pixel(self) -> float:
        """Detect mana using pixel color comparison"""
        if not self.mana_pixel_point or not self.mana_pixel_color:
            return None
            
        try:
            # Get current pixel color
            screenshot = pyautogui.screenshot()
            current_color = screenshot.getpixel(self.mana_pixel_point)
            
            # Calculate color distance from full mana color
            distance = self.color_distance(current_color, self.mana_pixel_color)
            
            # Binary detection: Full mana or low mana
            if distance < self.pixel_color_tolerance:
                return 100.0  # Full mana - no potion needed
            else:
                # Color changed = mana is not full, trigger potion use
                return 20.0  # Return low value to trigger potion if below threshold
                
        except Exception as e:
            print(f"Pixel detection error: {e}")
            return None
    
    def detect_health_percentage(self) -> float:
        """Detect current health percentage"""
        # Try pixel detection first (low CPU)
        pixel_result = self.detect_health_percentage_pixel()
        if pixel_result is not None:
            return pixel_result
            
        # Fallback to color detection
        try:
            screenshot = pyautogui.screenshot(region=self.health_bar_region)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Red color range for health
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = mask1 + mask2
            
            total_pixels = img.shape[0] * img.shape[1]
            red_pixels = cv2.countNonZero(mask)
            
            return (red_pixels / total_pixels) * 100
        except:
            return 100.0

    def detect_mana_percentage(self) -> float:
        """Detect current mana percentage"""
        # Try pixel detection first (low CPU)
        pixel_result = self.detect_mana_percentage_pixel()
        if pixel_result is not None:
            return pixel_result
            
        # Fallback to color detection
        try:
            screenshot = pyautogui.screenshot(region=self.mana_bar_region)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Blue color range for mana
            lower_blue = np.array([100, 50, 50])
            upper_blue = np.array([130, 255, 255])
            mask = cv2.inRange(hsv, lower_blue, upper_blue)
            
            total_pixels = img.shape[0] * img.shape[1]
            blue_pixels = cv2.countNonZero(mask)
            
            return (blue_pixels / total_pixels) * 100
        except:
            return 100.0

    def update_game_state(self):
        """Update current game state"""
        self.game_state.health_percentage = self.detect_health_percentage()
        self.game_state.mana_percentage = self.detect_mana_percentage()
        self.game_state.active_effects = self.detect_active_utility_effects()

    def is_poe_window_focused(self) -> bool:
        """Check if Path of Exile window is currently focused"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows implementation using ctypes (more reliable than PowerShell)
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Import Windows APIs
                    user32 = ctypes.windll.user32
                    kernel32 = ctypes.windll.kernel32
                    psapi = ctypes.windll.psapi
                    
                    # Get foreground window
                    hwnd = user32.GetForegroundWindow()
                    
                    # Get process ID
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    
                    # Open process
                    PROCESS_QUERY_INFORMATION = 0x0400
                    PROCESS_VM_READ = 0x0010
                    process_handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
                    
                    if process_handle:
                        # Get process name
                        executable = ctypes.create_unicode_buffer(512)
                        psapi.GetModuleBaseNameW(process_handle, None, executable, 512)
                        kernel32.CloseHandle(process_handle)
                        
                        # Remove .exe extension if present
                        process_name = executable.value
                        if process_name.lower().endswith('.exe'):
                            process_name = process_name[:-4]
                        
                        # Check if it's Path of Exile
                        process_lower = process_name.lower()
                        return ('pathofexile' in process_lower or 
                               process_lower == 'pathofexile' or
                               process_lower == 'pathofexile_x64' or
                               process_lower == 'pathofexilesteam')
                except:
                    # Fallback to PowerShell method if ctypes fails
                    ps_script = """
                    Add-Type @"
                        using System;
                        using System.Diagnostics;
                        using System.Runtime.InteropServices;
                        public class Win32 {
                            [DllImport("user32.dll")]
                            public static extern IntPtr GetForegroundWindow();
                            [DllImport("user32.dll")]
                            public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
                        }
"@
                    $hwnd = [Win32]::GetForegroundWindow()
                    $pid = 0
                    [Win32]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
                    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($process) {
                        $processName = $process.ProcessName.ToLower()
                        if ($processName -like '*pathofexile*' -or $processName -eq 'pathofexile' -or $processName -eq 'pathofexile_x64' -or $processName -eq 'pathofexilesteam') {
                            Write-Host "true"
                        } else {
                            Write-Host "false"
                        }
                    } else {
                        Write-Host "false"
                    }
                    """
                    result = subprocess.run(['powershell', '-Command', ps_script], 
                                          capture_output=True, text=True, timeout=1)
                    return result.stdout.strip().lower() == "true"
                
            elif system == "Linux":
                # Linux implementation using xdotool (requires xdotool package)
                try:
                    # Get the active window ID
                    result = subprocess.run(['xdotool', 'getactivewindow'], 
                                          capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        window_id = result.stdout.strip()
                        # Get the window name
                        result = subprocess.run(['xdotool', 'getwindowname', window_id], 
                                              capture_output=True, text=True, timeout=1)
                        if result.returncode == 0:
                            window_name = result.stdout.strip().lower()
                            return 'path of exile' in window_name
                except FileNotFoundError:
                    # xdotool not installed, try wmctrl
                    try:
                        result = subprocess.run(['wmctrl', '-l', '-p'], 
                                              capture_output=True, text=True, timeout=1)
                        if result.returncode == 0:
                            # Check if any Path of Exile window is active
                            # This is less accurate as it doesn't check focus
                            lines = result.stdout.strip().split('\n')
                            for line in lines:
                                if 'path of exile' in line.lower():
                                    return True
                    except FileNotFoundError:
                        print("Warning: Neither xdotool nor wmctrl found. Install one for window focus detection.")
                        return True  # Default to true if we can't detect
                        
            elif system == "Darwin":  # macOS
                # macOS implementation using osascript
                script = """
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    if frontApp is "Path of Exile" then
                        return "true"
                    else
                        return "false"
                    end if
                end tell
                """
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True, timeout=1)
                return result.stdout.strip().lower() == "true"
                
            else:
                # Unknown system, default to true
                return True
                
        except Exception as e:
            # If any error occurs, default to true to avoid breaking functionality
            if hasattr(self, '_last_focus_error_time'):
                # Only print error once every 30 seconds to avoid spam
                if time.time() - self._last_focus_error_time > 30:
                    print(f"Window focus detection error: {e}")
                    self._last_focus_error_time = time.time()
            else:
                print(f"Window focus detection error: {e}")
                self._last_focus_error_time = time.time()
            return True

    def print_status(self):
        """Print current status"""
        health = self.game_state.health_percentage
        mana = self.game_state.mana_percentage
        
        # Format health display
        if self.game_state.health_current is not None and self.game_state.health_max is not None:
            health_str = f"HP: {self.game_state.health_current}/{self.game_state.health_max} ({health:.1f}%)"
        else:
            health_str = f"HP: {health:.1f}%"
        
        # Format mana display
        if self.game_state.mana_current is not None and self.game_state.mana_max is not None:
            mana_str = f"MP: {self.game_state.mana_current}/{self.game_state.mana_max} ({mana:.1f}%)"
        else:
            mana_str = f"MP: {mana:.1f}%"
        
        status_parts = [health_str, mana_str]
        
        # Add window focus indicator
        if self.require_window_focus:
            focus_status = "POE:Active" if self.poe_window_focused else "POE:Inactive"
            status_parts.insert(0, focus_status)
        
        # Show active potions
        active_potions = []
        current_time = time.time()
        for slot in self.slots:
            if current_time < slot.active_until:
                remaining = slot.active_until - current_time
                active_potions.append(f"{slot.subtype.value}({remaining:.0f}s)")
        
        if active_potions:
            status_parts.append(f"Active: {', '.join(active_potions)}")
        
        # Show available potions
        available = []
        for slot in self.slots:
            if slot.uses_remaining > 0:
                available.append(f"{slot.subtype.value}({slot.uses_remaining})")
        
        if available:
            status_parts.append(f"Available: {', '.join(available)}")
        
        print(" | ".join(status_parts), end='\r')

    def main_loop(self):
        """Main monitoring loop"""
        print("Advanced Potion Manager started. Press Ctrl+C to stop.")
        if self.require_window_focus:
            print("Window focus detection enabled - potions will only be used when Path of Exile is active.")
        last_scan_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check window focus if required
                if self.require_window_focus:
                    self.poe_window_focused = self.is_poe_window_focused()
                    
                    # Only process potions if window is focused
                    if self.poe_window_focused:
                        # Update game state
                        self.update_game_state()
                        
                        # Rescan slots periodically
                        if current_time - last_scan_time > 5:  # Every 5 seconds
                            self.scan_all_slots()
                            last_scan_time = current_time
                        
                        # Process potions
                        self.process_health_potions()
                        self.process_mana_potions()
                        self.process_utility_potions()
                else:
                    # Window focus not required, process normally
                    # Update game state
                    self.update_game_state()
                    
                    # Rescan slots periodically
                    if current_time - last_scan_time > 5:  # Every 5 seconds
                        self.scan_all_slots()
                        last_scan_time = current_time
                    
                    # Process potions
                    self.process_health_potions()
                    self.process_mana_potions()
                    self.process_utility_potions()
                
                # Print status (always show status regardless of focus)
                self.print_status()
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\nStopping potion manager...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)

    def start(self):
        """Start the potion manager"""
        self.running = True
        self.scan_all_slots()  # Initial scan
        self.main_loop()

    def stop(self):
        """Stop the potion manager"""
        self.running = False

# This module provides the AdvancedPotionManager class for potion management.
# For the GUI interface, use potions_gui.py