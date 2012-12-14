import os

from loader import Client

# Hatari documentation: http://hg.tuxfamily.org/mercurialroot/hatari/hatari/raw-file/tip/doc/manual.html
#
# Config file entry to provide filename to save on exit:
#
# [Memory]
# nMemorySize = 1
# bAutoSave = TRUE
# szMemoryCaptureFileName = /path/to/save/game.hatari
# szAutoSaveFileName = /path/to/save/game.hatari
#
# start using: hatari -c /path/to/config.cfg
#
# Info on saving state on exit using F12 key: http://www.atari-forum.com/viewtopic.php?f=51&t=22422 
#
# "changed all [ShortcutsWithoutModifiers] in the cfg to 0 exept KeyQuit.
# Changed it to "keyQuit = 293" F12 is quit and you need the alt tab to go to
# other options."

class HatariClient(Client):
    pass

Client.register("hatari", HatariClient)
