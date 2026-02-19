import vlc
from pathlib import PurePath, Path
import json
import threading
from pynput import keyboard

class VideoPlayer:
    """
    A video player class using VLC for playing videos in fullscreen mode.

    This class manages video playback for an RFID-based interactive display system.
    It plays videos associated with puck codes (RFID identifiers) and automatically
    returns to a welcome video after each video completes. The class handles video
    playlist management, configuration loading, and provides utilities for adding
    new puck-to-video associations.

    Keyboard input is captured globally via pynput so it works regardless of
    which window has focus (VLC fullscreen won't steal input).
    """
    def __init__(self) -> None:
        self.instance: vlc.Instance = vlc.Instance("--fullscreen", "--no-video-title-show", "--no-osd")
        self.player: vlc.MediaPlayer = self.instance.media_player_new()
        self.playlist_player: vlc.MediaListPlayer = self.instance.media_list_player_new()
        self.playlist_player.set_media_player(self.player)
        self.config = json.load(open('config.json','r'))
        self._line_buffer = []
        self._line_ready = threading.Event()
        self._current_line = ""
        self._start_keyboard_listener()
        self.welcome_video_media = self.instance.media_new(self._get_video_path('welcome_video'))
        self.welcome_video_media.add_option("input-repeat=-1")
        self.play_welcome()

    def _start_keyboard_listener(self):
        """Start a global keyboard listener that captures input regardless of window focus."""
        def on_press(key):
            try:
                char = key.char
                if char is not None:
                    self._line_buffer.append(char)
            except AttributeError:
                if key == keyboard.Key.enter:
                    self._current_line = ''.join(self._line_buffer)
                    self._line_buffer.clear()
                    self._line_ready.set()
                elif key == keyboard.Key.backspace and self._line_buffer:
                    self._line_buffer.pop()
                elif key == keyboard.Key.space:
                    self._line_buffer.append(' ')

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

    def _read_line(self, prompt=""):
        """Read a line of keyboard input globally (focus-independent). Blocks until Enter."""
        if prompt:
            print(prompt, end='', flush=True)
        self._line_ready.clear()
        self._line_ready.wait()
        line = self._current_line
        print(line)
        return line

    def shutdown_vlc(self):
        """
        gracefully exit vlc.
        """
        self.player.stop()
        self.player.release()
        self.playlist_player.release()
        self.instance.release()

    def _get_video_path(self ,puck_code):
        return str(PurePath(self.config['metadata']['data_folder'], self.config[puck_code]))

    def play_video(self, puck_code):
        """
        plays a video then loops the welcome video.
        """
        self.playlist_player.set_playback_mode(vlc.PlaybackMode.default)

        if not puck_code in self.config:
            print(f"code {puck_code} not found")
            return

        media_path = self._get_video_path(puck_code)
        print("play_video called with:", puck_code, "filename: ", media_path)
        media = self.instance.media_new(media_path)
        self.player.set_media(media)
        self.player.play()
        self.player.set_fullscreen(True)
        print("after play(): state=", self.player.get_state(), "is_playing=", self.player.is_playing())


        def on_first_end(event):
                print("on_first_end fired. state=", self.player.get_state())
                threading.Timer(0.05, self._play_welcome_loop).start()
        # keep callback reference to avoid GC
        self._end_callback = on_first_end
        mgr = self.player.event_manager()
        mgr.event_detach(vlc.EventType.MediaPlayerEndReached)
        mgr.event_attach(vlc.EventType.MediaPlayerEndReached, self._end_callback)
        print("attached EndReached handler")

    def _play_welcome_loop(self):
        welcome_path = self._get_video_path("welcome_video")
        welcome_media = self.instance.media_new(welcome_path)
        welcome_media.add_option("input-repeat=-1")  # loop welcome inside VLC
        self.player.set_media(welcome_media)
        self.player.play()
        self.player.set_fullscreen(True)
        print("welcome loop started")

    def save_dict(self):
        with open('config.json','w') as f:
            json.dump(self.config, f, indent=4)

    def play_welcome(self):
        self.play_video('welcome_video')

    def _add_new_puck(self, path = None):
        """
        subroutine for adding one puck code.
        """
        code = self._read_line('drop puck: ').strip()
        if not path:
            paths = sorted(Path(self.config['metadata']['data_folder']).iterdir())
            for i,k in enumerate(paths):
                print(f"{i+1}. {k.name}")
            choice = self._read_line('type the key number requested: ')
            self.config[code] = paths[int(choice)-1].name
        else:
            self.config[code] = path
        print(f"set code {code} to video file {self.config[code]}")
        return self.config[code]

    def add_new_pucks(self):
        """
        Lets user add [2 sided] puck[s]
        Updates config.json as well as the config dict.
        goes back to welcome screen at the end.
        """
        self.player.stop()
        add_pucks = True
        while add_pucks:
            path = self._add_new_puck()
            other_side = self._read_line("set other side? Y/n: ").strip().lower()
            if other_side == 'y' or other_side == '':
                self._add_new_puck(path)
            another_puck = self._read_line("set another puck? Y/n: ").strip().lower()
            if another_puck == 'n':
                add_pucks = False

        print('saving to dict...')
        self.save_dict()
        self.play_welcome()

if __name__=="__main__":
    v = VideoPlayer()
    try:
        while True:
            res = v._read_line().strip().lower()
            if res=='exit':
                v.shutdown_vlc()
                break
            elif res=='new':
                v.add_new_pucks()
            else:
                v.play_video(res)
    except KeyboardInterrupt:
        print("exiting gracefully")
        v.shutdown_vlc()
