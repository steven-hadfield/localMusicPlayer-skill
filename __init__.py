import sys
import time
from subprocess import check_call, PIPE, Popen, CalledProcessError
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_file_handler, intent_handler
from mycroft.util.log import LOG
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel

__author__ = 'colla69'

class CmusPlayer():
    def _cmus_call(self, args):
        try:
            check_call(["cmus-remote"] + args)
        except CalledProcessError as e:
            LOG.error("Failed to execute cmus-remote", e)

    def _cmus_query(self):
        status = {"tag": {}, "set": {}}
        try:
            (stdout, stderr) = Popen(['cmus-remote', '-Q'], stdout=PIPE).communicate()
            for line in stdout.splitlines():
                (meta_type, value) = line.decode(sys.getdefaultencoding()).split(" ", maxsplit=1)
                if meta_type in ["tag", "set"]:
                    (meta_tag, meta_value) = value.split(" ", maxsplit=1)
                    status[meta_type][meta_tag] = meta_value
                else:
                    status[meta_type] = value
            LOG.debug("cmus status: %s", status)
        except CalledProcessError as e:
            LOG.error("Failed to execute cmus-remote -Q", e)
        return status


    def start(self):
        check_call("screen -d -m -S cmus cmus &", shell=True)
        # TODO: Check if cmus is available rather than sleep
        time.sleep(1)
        # config player for usage
        self._cmus_call(['-C', 'view 2'])
        self._cmus_call(['-C', 'set softvol_state=70 70'])
        self._cmus_call(['-C', 'set continue=true'])
        time.sleep(1)

    def stop(self):
        self._cmus_call(["-C", "quit"])

    def play(self):
        self._cmus_call(["-p"])

    def pause(self):
        self._cmus_call(["-u"])

    def next(self):
        self._cmus_call(["-n"])

    def prev(self):
        self._cmus_call(["-N"])

    def search(self, text):
        self._cmus_call(["-C", '/' + text])
        self._cmus_call(["-C", 'win-activate'])

    def refresh_library(self, path):
        self._cmus_call(["-C", 'clear'])
        LOG.info('reloading music files from: %s', path)
        self._cmus_call(["-C", 'add ' + path])

    def show(self):
        try:
            check_call(['x-terminal-emulator', '-e', 'screen -r'])
        except CalledProcessError as e:
            LOG.error("Failed to execute x-terminal-emulator", e)

    def is_running(self):
        (stdout, stderr) = Popen('ps ax | grep cmus | grep -v " grep"', shell=True, stdout=PIPE).communicate()
        check = stdout.splitlines()
        return len(check) != 0

    def is_shuffle(self):
        config = self._cmus_query()["set"]
        return "shuffle" in config and config["shuffle"] == "true"

    def toggle_shuffle(self):
        state = "false" if self.is_shuffle() else "true"
        self._cmus_call(['-C', 'set shuffle=%s'.format(state)])

    def get_status(self):
        meta = self._cmus_query()
        if "status" in meta and meta["status"] == "stopped":
            return None

        tags = meta["tag"]

        status = tags["title"] if "title" in tags else "Song"

        if "album" in tags:
            status = status + " from " + tags["album"]

        if "artist" in tags:
            status = status + " by " + tags["artist"]
        elif "albumartist" in tags:
            status = status + " by " + tags["albumartist"]
        elif "composer" in tags:
            status = status + " by " + tags["composer"]

        return status


class Localmusicplayer(CommonPlaySkill):
    def CPS_match_query_phrase(self, phrase):
        #library = open('/home/cola/.config/cmus/lib.pl')
        #for line in library:
        #    mySongs.append(line.strip())

        #LOG.info(mySongs)

        return phrase, CPSMatchLevel.TITLE

    def CPS_start(self, phrase, data):
        #search_player(phrase)
        pass

    def __init__(self):
        super().__init__(name="Local Music Player Skill")
        self.player = CmusPlayer()
        # Initialize working variables used within the skill.
        self.music_source = self.settings.get("musicsource", "")
        # init cmus player
        self.activate_player()

    def getspoken_shufflestate(self):
        spoken = "active" if self.player.is_shuffle() else "nonoperational"
        self.speak(spoken)

    @intent_file_handler('play.music.intent')
    def handle_play_music_ntent(self, message):
        self.activate_player()
        self.player.play()

    @intent_file_handler('pause.music.intent')
    def handle_pause_music_intent(self, message):
        self.activate_player()
        self.player.pause()

    @intent_file_handler('reload.library.intent')
    def handle_reload_library_intent(self, message):
        self.player.refresh_library(self.music_source)
        self.speak_dialog("refresh.library")

    @intent_file_handler('shuffling.library.intent')
    def handle_shuffling_library_intent(self, message):
        self.getspoken_shufflestate()

    @intent_file_handler('next.music.intent')
    def handle_next_music_intent(self, message):
        self.activate_player()
        self.player.next()

    @intent_file_handler('prev.music.intent')
    def handle_prev_music_intent(self, message):
        self.activate_player()
        self.player.prev()

    @intent_file_handler('show.music.intent')
    def handle_show_music_intent(self, message):
        self.activate_player()
        self.player.show()

    @intent_file_handler('status.music.intent')
    def handle_status_music_intent(self, message):
        status = self.player.get_status() if self.player.is_running() else None
        if not status:
            status = "No song is playing"
        self.speak(status)

    @intent_file_handler('change.shuffling.music.intent')
    def handle_change_shuffle_music_intent(self, message):
        self.player.toggle_shuffle()
        self.getspoken_shufflestate()

    @intent_handler(IntentBuilder("search.music.intent").require("search.music").require("SongToPlay").build())
    def handle_search_music_intent(self, message):
        songtoplay = message.data.get("SongToPlay")
        self.activate_player()
        LOG.info("playing %s", songtoplay)
        self.player.search(songtoplay)

    def activate_player(self):
        if not self.player.is_running():
            self.player.start()
            self.player.refresh_library(self.music_source)

    def converse(self, utterances, lang="en-us"):
        return False

    def stop(self):
        pass
        #if self.player.is_running():
        #  self.player.stop()


def create_skill():
    return Localmusicplayer()
