#!/usr/bin/env python3
"""
Calibration script for RFID Image Display System.
Waits for RFID tags and allows mapping them to images.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


CONFIG_FILE = "config.json"
IMAGES_DIR = "data/images"


def load_config():
    """Load configuration from config.json, create default if it doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return create_default_config()
    else:
        return create_default_config()


def create_default_config():
    """Create a default configuration file."""
    default_config = {
        "rfid_mappings": {},
        "inactivity_timeout": 30,
        "welcome_image": "welcome.jpg"
    }
    save_config(default_config)
    return default_config


def save_config(config):
    """Save configuration to config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving config: {e}")


def get_image_files():
    """Get list of image files from data/images directory."""
    images_dir = Path(IMAGES_DIR)
    if not images_dir.exists():
        return []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    image_files = []
    
    for file in images_dir.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            image_files.append(file.name)
    
    return sorted(image_files)


def show_image_selection_dialog(rfid_code):
    """Show a dialog to select an image for the given RFID code."""
    image_files = get_image_files()
    
    if not image_files:
        messagebox.showerror(
            "No Images Found",
            f"No image files found in {IMAGES_DIR}.\n"
            "Please add image files to the directory first."
        )
        return None
    
    # Create dialog window
    dialog = tk.Toplevel()
    dialog.title(f"Map RFID: {rfid_code}")
    dialog.geometry("400x150")
    dialog.transient()
    dialog.grab_set()
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    selected_image = [None]  # Use list to allow modification in nested function
    
    # Label
    label = tk.Label(
        dialog,
        text=f"Select image for RFID code: {rfid_code}",
        font=("Arial", 10)
    )
    label.pack(pady=10)
    
    # Combobox
    combo_var = tk.StringVar()
    combo = ttk.Combobox(dialog, textvariable=combo_var, values=image_files, width=40)
    combo.pack(pady=5)
    combo.current(0)  # Select first item by default
    
    # Buttons frame
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    
    def save_mapping():
        selected = combo_var.get()
        if selected:
            selected_image[0] = selected
            dialog.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select an image.")
    
    def cancel():
        dialog.destroy()
    
    save_btn = tk.Button(button_frame, text="Save Mapping", command=save_mapping, width=12)
    save_btn.pack(side=tk.LEFT, padx=5)
    
    cancel_btn = tk.Button(button_frame, text="Cancel", command=cancel, width=12)
    cancel_btn.pack(side=tk.LEFT, padx=5)
    
    # Bind Enter key to save
    combo.bind('<Return>', lambda e: save_mapping())
    dialog.bind('<Escape>', lambda e: cancel())
    
    # Focus on combobox
    combo.focus_set()
    
    # Wait for dialog to close
    dialog.wait_window()
    
    return selected_image[0]


def main():
    """Main calibration loop."""
    print("RFID Calibration Tool")
    print("=" * 50)
    print(f"Images directory: {IMAGES_DIR}")
    print("Waiting for RFID tags...")
    print("(Press Ctrl+C to exit)")
    print("=" * 50)
    
    # Initialize tkinter root (hidden)
    root = tk.Tk()
    root.withdraw()
    
    config = load_config()
    image_files = get_image_files()
    
    if not image_files:
        print(f"\nERROR: No image files found in {IMAGES_DIR}")
        print("Please add image files to the directory first.")
        return
    
    print(f"\nFound {len(image_files)} image(s) in {IMAGES_DIR}")
    print("\nInstructions:")
    print("1. Place an RFID tag near the reader")
    print("2. Select the corresponding image from the dropdown")
    print("3. Click 'Save Mapping'")
    print("4. Repeat for all RFID tags\n")
    
    try:
        while True:
            # Wait for RFID input
            print("\nWaiting for RFID tag...")
            rfid_code = input().strip()
            
            if not rfid_code:
                continue
            
            print(f"Detected RFID code: {rfid_code}")
            
            # Check if already mapped
            if rfid_code in config.get("rfid_mappings", {}):
                existing_image = config["rfid_mappings"][rfid_code]
                response = messagebox.askyesno(
                    "Already Mapped",
                    f"RFID code {rfid_code} is already mapped to:\n{existing_image}\n\n"
                    "Do you want to update it?"
                )
                if not response:
                    print("Skipped.")
                    continue
            
            # Show image selection dialog
            selected_image = show_image_selection_dialog(rfid_code)
            
            if selected_image:
                # Update config
                if "rfid_mappings" not in config:
                    config["rfid_mappings"] = {}
                
                config["rfid_mappings"][rfid_code] = selected_image
                save_config(config)
                print(f"✓ Mapped {rfid_code} -> {selected_image}")
            else:
                print("✗ Mapping cancelled or no image selected")
    
    except KeyboardInterrupt:
        print("\n\nCalibration stopped by user.")
        print(f"Configuration saved to {CONFIG_FILE}")
    except EOFError:
        print("\n\nInput stream closed.")
    finally:
        root.destroy()


if __name__ == "__main__":
    main()

