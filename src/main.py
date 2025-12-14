#!/usr/bin/env python3
"""
Main display program for RFID Image Display System.
Displays images based on RFID tag input and shows welcome image after inactivity.
"""

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
from pynput import keyboard


CONFIG_FILE = "config.json"
IMAGES_DIR = "data/images"


class RFIDImageDisplay:
    def __init__(self):
        self.root = tk.Tk()
        self.config = self.load_config()
        self.current_image = None
        self.inactivity_timer = None
        self.rfid_thread = None
        self.running = True
        self.rfid_buffer = ""  # Buffer for RFID input characters
        
        # Setup window
        self.setup_window()
        
        # Load and display welcome image initially
        self.display_welcome_image()
        
        # Start inactivity timer
        self.reset_inactivity_timer()
        
        # Start RFID input capture using pynput (works globally)
        self.setup_rfid_capture()
    
    def load_config(self):
        """Load configuration from config.json."""
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(
                f"Configuration file {CONFIG_FILE} not found.\n"
                "Please run calibrate.py first to set up the system."
            )
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate config structure
            if "rfid_mappings" not in config:
                config["rfid_mappings"] = {}
            if "inactivity_timeout" not in config:
                config["inactivity_timeout"] = 30
            if "welcome_image" not in config:
                config["welcome_image"] = "welcome.jpg"
            
            return config
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"Error loading config: {e}")
    
    def setup_window(self):
        """Setup the fullscreen display window."""
        self.root.title("RFID Image Display")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')
        
        # Remove window decorations
        self.root.overrideredirect(True)
        
        # Bind Escape key to exit
        self.root.bind('<Escape>', lambda e: self.quit())
        
        # Create label for displaying images
        self.image_label = tk.Label(self.root, bg='black')
        self.image_label.pack(expand=True, fill='both')
    
    def get_image_path(self, filename):
        """Get full path to an image file."""
        return Path(IMAGES_DIR) / filename
    
    def load_and_display_image(self, image_filename):
        """Load and display an image fullscreen."""
        image_path = self.get_image_path(image_filename)
        
        if not image_path.exists():
            print(f"Warning: Image not found: {image_path}")
            return False
        
        try:
            # Load image with PIL
            pil_image = Image.open(image_path)
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate scaling to fit screen while maintaining aspect ratio
            img_width, img_height = pil_image.size
            scale_w = screen_width / img_width
            scale_h = screen_height / img_height
            scale = min(scale_w, scale_h)
            
            # Resize image
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_image = ImageTk.PhotoImage(pil_image)
            
            # Update label
            self.image_label.config(image=self.current_image)
            self.image_label.image = self.current_image  # Keep a reference
            
            return True
        except Exception as e:
            print(f"Error loading image {image_filename}: {e}")
            return False
    
    def display_welcome_image(self):
        """Display the welcome image."""
        welcome_image = self.config.get("welcome_image", "welcome.jpg")
        if not self.load_and_display_image(welcome_image):
            # If welcome image not found, show a default message
            self.image_label.config(
                image='',
                text=f"Welcome\n\n(Image: {welcome_image} not found)",
                fg='white',
                font=('Arial', 24),
                justify='center'
            )
    
    def display_rfid_image(self, rfid_code):
        """Display image corresponding to RFID code."""
        mappings = self.config.get("rfid_mappings", {})
        
        if rfid_code in mappings:
            image_filename = mappings[rfid_code]
            if self.load_and_display_image(image_filename):
                print(f"Displayed image for RFID {rfid_code}: {image_filename}")
            else:
                print(f"Failed to load image for RFID {rfid_code}: {image_filename}")
                self.display_welcome_image()
        else:
            print(f"RFID code {rfid_code} not found in mappings")
            self.display_welcome_image()
    
    def reset_inactivity_timer(self):
        """Reset the inactivity timer."""
        # Cancel existing timer if any
        if self.inactivity_timer:
            self.root.after_cancel(self.inactivity_timer)
        
        # Get timeout from config
        timeout_seconds = self.config.get("inactivity_timeout", 30) * 1000  # Convert to milliseconds
        
        # Schedule welcome image display
        self.inactivity_timer = self.root.after(
            timeout_seconds,
            self.display_welcome_image
        )
    
    def _process_rfid_input(self, rfid_code):
        """Process RFID input on main thread."""
        rfid_code = rfid_code.strip()
        if rfid_code:
            print(f"Received RFID code: {rfid_code}")
            self.display_rfid_image(rfid_code)
            self.reset_inactivity_timer()
    
    def setup_rfid_capture(self):
        """Setup RFID input capture using pynput (works globally, regardless of window focus)."""
        print("RFID capture active. Waiting for tags...")
        
        # Start pynput keyboard listener in background thread
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press_pynput,
            suppress=False  # Don't suppress the key events (let them pass through)
        )
        self.keyboard_listener.start()
    
    def on_key_press_pynput(self, key):
        """Handle key press events from pynput to build RFID code buffer."""
        try:
            # Handle Enter key
            if key == keyboard.Key.enter:
                if self.rfid_buffer:
                    rfid_code = self.rfid_buffer.strip()
                    self.rfid_buffer = ""  # Reset buffer
                    # Schedule UI update on main thread
                    self.root.after(0, lambda code=rfid_code: self._process_rfid_input(code))
                return
            
            # Handle Escape key to exit
            if key == keyboard.Key.esc:
                self.root.after(0, self.quit)
                return
            
            # Handle character keys
            if hasattr(key, 'char') and key.char and key.char.isprintable():
                self.rfid_buffer += key.char
        except Exception as e:
            print(f"Error handling key press: {e}")
    
    def quit(self):
        """Quit the application."""
        self.running = False
        # Stop keyboard listener
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            self.keyboard_listener.stop()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the main loop."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.quit()


def main():
    """Main entry point."""
    try:
        app = RFIDImageDisplay()
        app.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()

