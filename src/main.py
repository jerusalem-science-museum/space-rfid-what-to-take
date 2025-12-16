#!/usr/bin/env python3
"""
Main display program for RFID Image Display System.
Displays images and videos based on RFID tag input and shows welcome image after inactivity.
"""

import json
import os
import threading
import time
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
import cv2


CONFIG_FILE = "config.json"
IMAGES_DIR = "data/images"


class RFIDImageDisplay:
    def __init__(self):
        self.root = tk.Tk()
        self.config = self.load_config()
        self.current_image = None
        self.inactivity_timer = None
        self.running = True
        self.rfid_buffer = ""  # Buffer for RFID input characters
        self.video_cap = None  # Video capture object
        self.video_playing = False
        self.video_thread = None
        self.stop_video_flag = threading.Event()
        
        # Setup window
        self.setup_window()
        
        # Ensure window stays focused (since there's no mouse)
        self.root.focus_force()
        
        # Load and display welcome image initially
        self.display_welcome_image()
        
        # Start inactivity timer
        self.reset_inactivity_timer()
        
        # Start RFID input capture using stdin in a separate thread
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
        self.root.title("RFID Media Display")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')
        
        # Bind Escape key to exit
        self.root.bind('<Escape>', lambda e: self.quit())
        
        # Bind keyboard events for RFID input capture
        # Capture all keypresses to build RFID code
        self.root.bind('<KeyPress>', self.on_key_press)
        
        # Create label for displaying images
        self.image_label = tk.Label(self.root, bg='black')
        self.image_label.pack(expand=True, fill='both')
    
    def get_media_path(self, filename):
        """Get full path to a media file (image or video)."""
        return Path(IMAGES_DIR) / filename
    
    def is_video_file(self, filename):
        """Check if file is a video based on extension."""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        return Path(filename).suffix.lower() in video_extensions
    
    def stop_video(self):
        """Stop any currently playing video."""
        if self.video_playing:
            self.stop_video_flag.set()
            self.video_playing = False
            if self.video_cap is not None:
                self.video_cap.release()
                self.video_cap = None
            if self.video_thread is not None:
                self.video_thread.join(timeout=1.0)
                self.video_thread = None
    
    def play_video(self, video_filename):
        """Play a video file fullscreen."""
        video_path = self.get_media_path(video_filename)
        
        if not video_path.exists():
            print(f"Warning: Video not found: {video_path}")
            return False
        
        # Stop any currently playing video
        self.stop_video()
        
        try:
            # Open video file
            self.video_cap = cv2.VideoCapture(str(video_path))
            
            if not self.video_cap.isOpened():
                print(f"Error: Could not open video {video_filename}")
                return False
            
            # Get video properties
            fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30  # Default FPS if not available
            
            self.video_playing = True
            self.stop_video_flag.clear()
            
            # Start video playback in a separate thread
            self.video_thread = threading.Thread(target=self._video_loop, args=(fps,), daemon=True)
            self.video_thread.start()
            
            return True
        except Exception as e:
            print(f"Error loading video {video_filename}: {e}")
            self.stop_video()
            return False
    
    def _video_loop(self, fps):
        """Video playback loop running in a separate thread."""
        frame_delay = int(1000 / fps) if fps > 0 else 33  # milliseconds per frame
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        while self.video_playing and not self.stop_video_flag.is_set():
            ret, frame = self.video_cap.read()
            
            if not ret:
                # Video ended, go back to welcome image
                self.video_playing = False
                self.root.after(0, self._on_video_finished)
                break
            
            # Resize frame to fit screen while maintaining aspect ratio
            frame_height, frame_width = frame.shape[:2]
            scale_w = screen_width / frame_width
            scale_h = screen_height / frame_height
            scale = min(scale_w, scale_h)
            
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            
            frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Convert BGR to RGB for tkinter
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Convert to PhotoImage and update on main thread
            self.root.after(0, self._update_video_frame, pil_image)
            
            # Wait for next frame
            time.sleep(frame_delay / 1000.0)
        
        # Cleanup
        if self.video_cap is not None:
            self.video_cap.release()
            self.video_cap = None
    
    def _on_video_finished(self):
        """Handle video playback completion - return to welcome image."""
        self.stop_video()
        self.display_welcome_image()
        self.reset_inactivity_timer()
    
    def _update_video_frame(self, pil_image):
        """Update video frame on main thread."""
        if not self.video_playing:
            return
        
        try:
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update label
            self.image_label.config(image=photo)
            self.image_label.image = photo  # Keep a reference
        except Exception as e:
            print(f"Error updating video frame: {e}")
    
    def load_and_display_image(self, image_filename):
        """Load and display an image fullscreen."""
        # Stop any playing video first
        self.stop_video()
        
        image_path = self.get_media_path(image_filename)
        
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
    
    def load_and_display_media(self, media_filename):
        """Load and display an image or video file."""
        if self.is_video_file(media_filename):
            return self.play_video(media_filename)
        else:
            return self.load_and_display_image(media_filename)
    
    def display_welcome_image(self):
        """Display the welcome image."""
        # Stop any playing video first
        self.stop_video()
        
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
    
    def display_rfid_media(self, rfid_code):
        """Display image or video corresponding to RFID code."""
        mappings = self.config.get("rfid_mappings", {})
        
        if rfid_code in mappings:
            media_filename = mappings[rfid_code]
            if self.load_and_display_media(media_filename):
                media_type = "video" if self.is_video_file(media_filename) else "image"
                print(f"Displayed {media_type} for RFID {rfid_code}: {media_filename}")
                # Only reset inactivity timer for images, not videos
                # Videos will reset it when they finish
                if not self.is_video_file(media_filename):
                    self.reset_inactivity_timer()
            else:
                print(f"Failed to load media for RFID {rfid_code}: {media_filename}")
                self.display_welcome_image()
        else:
            print(f"RFID code {rfid_code} not found in mappings")
            self.display_welcome_image()
    
    def reset_inactivity_timer(self):
        """Reset the inactivity timer."""
        # Cancel existing timer if any
        if self.inactivity_timer:
            self.root.after_cancel(self.inactivity_timer)
            self.inactivity_timer = None
        
        # Don't set inactivity timer if video is playing
        if self.video_playing:
            return
        
        # Get timeout from config
        timeout_seconds = self.config.get("inactivity_timeout", 30) * 1000  # Convert to milliseconds
        
        # Schedule welcome image display
        self.inactivity_timer = self.root.after(
            timeout_seconds,
            self._on_inactivity_timeout
        )
    
    def _on_inactivity_timeout(self):
        """Handle inactivity timeout - only if not playing video."""
        if not self.video_playing:
            self.display_welcome_image()
    
    def _process_rfid_input(self, rfid_code):
        """Process RFID input on main thread."""
        rfid_code = rfid_code.strip()
        if rfid_code:
            print(f"Received RFID code: {rfid_code}")
            self.display_rfid_media(rfid_code)
            self.reset_inactivity_timer()
    
    def setup_rfid_capture(self):
        """Setup RFID input capture - using tkinter keyboard events."""
        print("RFID capture active. Waiting for tags...")
        # Keyboard events are handled by on_key_press() binding
    
    def on_key_press(self, event):
        """Handle key press events to build RFID code."""
        try:
            # Handle Enter key - process the RFID code
            if event.keysym == 'Return' or event.keysym == 'KP_Enter':
                if self.rfid_buffer:
                    rfid_code = self.rfid_buffer.strip()
                    self.rfid_buffer = ""  # Reset buffer
                    self._process_rfid_input(rfid_code)
                return
            
            # Handle Escape key to exit
            if event.keysym == 'Escape':
                self.quit()
                return
            
            # Handle character keys - add to buffer
            if event.char and event.char.isprintable():
                self.rfid_buffer += event.char
        except Exception as e:
            print(f"Error handling key press: {e}")
    
    def quit(self):
        """Quit the application."""
        self.running = False
        # Stop any playing video
        self.stop_video()
        # The RFID thread is a daemon thread, so it will exit automatically
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

