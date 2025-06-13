#!/usr/bin/env python3
"""
Find Path of Exile process name on Windows
"""

import subprocess
import platform

def find_poe_process():
    """List all processes and find Path of Exile"""
    if platform.system() != "Windows":
        print("This script is for Windows only")
        return
        
    ps_script = """
    Get-Process | Where-Object {
        $_.ProcessName -like '*path*' -or 
        $_.ProcessName -like '*exile*' -or 
        $_.ProcessName -like '*poe*' -or
        $_.MainWindowTitle -like '*path of exile*'
    } | Select-Object ProcessName, Id, MainWindowTitle | Format-Table -AutoSize
    """
    
    print("Searching for Path of Exile processes...")
    print("=" * 60)
    
    result = subprocess.run(['powershell', '-Command', ps_script], 
                          capture_output=True, text=True, timeout=5)
    
    if result.returncode == 0 and result.stdout.strip():
        print("Found potential Path of Exile processes:")
        print(result.stdout)
    else:
        print("No Path of Exile processes found.")
        print("\nLet's list ALL processes with a window title:")
        
        ps_script_all = """
        Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | 
        Select-Object ProcessName, Id, MainWindowTitle | 
        Sort-Object ProcessName | Format-Table -AutoSize
        """
        
        result = subprocess.run(['powershell', '-Command', ps_script_all], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print(result.stdout)

if __name__ == "__main__":
    find_poe_process()
    print("\nPress Enter to exit...")
    input()