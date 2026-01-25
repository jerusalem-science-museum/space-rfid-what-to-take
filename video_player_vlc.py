import vlc
from pathlib import PurePath, Path
import json

class VideoPlayer:
    """
    A video player class using VLC for playing videos in fullscreen mode.
    
    This class manages video playback for an RFID-based interactive display system.
    It plays videos associated with puck codes (RFID identifiers) and automatically
    returns to a welcome video after each video completes. The class handles video
    playlist management, configuration loading, and provides utilities for adding
    new puck-to-video associations.
    
    The player operates in fullscreen mode and loops the welcome video when idle.
    When a puck code is detected, it plays the associated video, then returns to
    the welcome video loop.
    """
    def __init__(self) -> None:
        self.instance: vlc.Instance = vlc.Instance("--fullscreen", "--no-video-title-show")
        self.player: vlc.MediaPlayer = self.instance.media_player_new()
        self.playlist_player: vlc.MediaListPlayer = self.instance.media_list_player_new()
        self.playlist_player.set_media_player(self.player)
        self.config = json.load(open('config.json','r'))
        self.welcome_video_media = self.instance.media_new(self._get_video_path('welcome_video'))
        self.play_welcome()
    
    def _on_end(self, event):
        """
        since our playlist contains the video + welcome screen, 
        when we start a new media (i.e. the welcome screen), we want the playlist to repeat it infinitly.
        """
        self.playlist_player.set_playback_mode(vlc.PlaybackMode.repeat)


    def set_on_end(self,):
        """
        setup callback for end of first video in playlist.
        """
        event_manager = self.player.event_manager()
        self._end_callback = lambda event: self._on_end(event)
        event_manager.event_attach(vlc.EventType.MediaPlayerMediaChanged , self._end_callback)

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
        media = self.instance.media_new(media_path)
        self.player.set_media(media)
        self.player.play()
        #playlist = self.instance.media_list_new()
        #playlist.add_media(media)
        #playlist.add_media(self.welcome_video_media)
        #self.playlist_player.set_media_list(playlist)
        #self.playlist_player.play_item_at_index(0)

        def on_first_end(event):
            # Switch to welcome and loop it via event
            welcome_path = self._get_video_path("welcome_video")
            def loop_welcome(event):
                welcome_media = self.instance.media_new(welcome_path)
                self.player.set_media(welcome_media)
                self.player.play()
            mgr = self.player.event_manager()
            mgr.event_detach(vlc.EventType.MediaPlayerEndReached)  # Clear prior
            mgr.event_attach(vlc.EventType.MediaPlayerEndReached, loop_welcome)
            # Trigger first welcome play
            welcome_media = self.instance.media_new(welcome_path)
            self.player.set_media(welcome_media)
            self.player.play()

        mgr = self.player.event_manager()
        mgr.event_attach(vlc.EventType.MediaPlayerEndReached, on_first_end)


    def save_dict(self):
        with open('config.json','w') as f:
            json.dump(self.config, f, indent=4)

    def play_welcome(self):
        self.play_video('welcome_video')

    def _add_new_puck(self, path = None):
        """
        subroutine for adding one puck code.
        """
        code = input('drop puck: ').strip('\n')
        if not path:
            paths = sorted(Path(self.config['metadata']['data_folder']).iterdir())
            for i,k in enumerate(paths):
                print(f"{i+1}. {k.name}")
            choice = input('type the key number requested: ')
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
            other_side = input("set other side? Y/n: ").strip('\n').lower()
            if other_side == 'y' or other_side == '':
                self._add_new_puck(path)
            another_puck = input("set another puck? Y/n: ").strip('\n').lower()
            if another_puck == 'n':
                add_pucks = False
        
        print('saving to dict...')
        self.save_dict()
        self.play_welcome()

if __name__=="__main__":
    v = VideoPlayer()
    try:
        while True:
            res = input().strip('\n').lower()
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
