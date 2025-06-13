# GameScript - Advanced Potion Manager for Path of Exile

An automated potion management system that monitors your health/mana and uses potions intelligently.

## Installation

Install all dependencies with a single command:

```bash
pip install opencv-python numpy pyautogui Pillow
```

Or using the requirements file:

```bash
pip install -r requirements.txt
```

## Required Packages

- **opencv-python** - Computer vision library for image processing
- **numpy** - Numerical computing for array operations
- **pyautogui** - GUI automation and screenshot capture
- **Pillow** - Python Imaging Library for image manipulation

## Getting Started

### Step 1: Initial Setup (potion-setup.py)

The setup tool helps you configure the potion manager for your game resolution and UI layout.

**Run the setup:**
```bash
python potion-setup.py
```

**What it does:**
1. **Capture Reference Images**: Takes screenshots of your potion slots (both full and empty states)
2. **Configure Screen Regions**: Helps you define where your health/mana bars and potion slots are located
3. **Set Detection Points**: Configure pixel-based detection for accurate health/mana monitoring
4. **Save Configuration**: Creates a config file with all your settings

**Setup Instructions:**
1. Start Path of Exile and enter the game (not in menu)
2. Make sure your potions are visible in slots 1-5
3. Run the setup tool and follow the prompts:
   - Press 'C' to capture full potion images
   - Empty your potions and press 'C' again for empty states
   - Click to set health/mana detection points
   - Test the configuration with 'T'
4. Save your configuration when satisfied

### Step 2: Running the Potion Manager (potions_gui.py)

The GUI provides real-time monitoring and control over your potions.

**Run the GUI:**

On Windows (no console window):
```bash
pythonw potions_gui.py
```
Or double-click `potions_gui.pyw`

On Linux/Mac:
```bash
python potions_gui.py
```

**GUI Features:**

1. **Slot Display**: Shows all 5 potion slots with:
   - Current potion type (Health/Mana/Utility)
   - Uses remaining
   - Active status and duration
   - Visual preview of each slot

2. **Auto-Use Controls**: For each slot, you can enable:
   - **Auto-use**: Automatically uses the potion when needed
   - **Instant**: (Health only) Uses instantly when health drops below threshold
   - **Enduring**: (Mana only) Maintains mana flask effect continuously

3. **Monitoring Controls**:
   - **Start/Stop Monitoring**: Toggle automatic potion usage
   - **Scan Slots**: Manually rescan all potion slots
   - **Settings**: Adjust health/mana thresholds and other options

4. **Status Display**:
   - Current health and mana percentages
   - Active potion effects with remaining duration
   - Real-time activity log

## Usage Guide

### Basic Usage

1. **Start the game** and enter any area (not hideout/town)
2. **Run the potion GUI** (`python potions_gui.py`)
3. **Click "Scan Slots"** to detect your potions
4. **Configure each slot**:
   - Check "Auto-use" for potions you want automated
   - For health flasks: Check "Instant" for emergency use
   - For mana flasks: Check "Enduring" to maintain the effect
5. **Click "Start Monitoring"** to begin automation

### Threshold Settings

Click "Settings" to adjust:
- **Health Threshold**: Potions activate when health drops below this % (default: 50%)
- **Mana Threshold**: Potions activate when mana drops below this % (default: 30%)
- **Window Focus Detection**: Only use potions when Path of Exile is the active window

### Potion Priority

The system uses potions intelligently:
- **Health Potions**: Used when health drops below threshold, prioritizes instant flasks in emergencies
- **Mana Potions**: Maintains mana above threshold, can keep enduring effect active
- **Utility Potions**: Used when their buff expires (detects the green progress bar)

### Tips for Best Results

1. **Run the setup tool** for your specific game resolution
2. **Keep the game in windowed fullscreen** for best detection
3. **Don't cover the potion slots** with other windows
4. **Adjust thresholds** based on your build's needs
5. **Test in safe areas** before using in dangerous content

## Troubleshooting

**Potions not detected:**
- Run the setup tool again
- Ensure game UI scale is set to default
- Check that potion slots aren't covered

**Detection not accurate:**
- Adjust the pixel color tolerance in settings
- Re-run setup with better lighting conditions
- Make sure the game window isn't scaled

**Performance issues:**
- Enable "Window Focus Detection" to pause when game isn't active
- Close other resource-intensive applications
- Check CPU usage in task manager