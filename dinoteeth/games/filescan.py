import os, sys

from persistent import Persistent

from .. import utils


class GameScanBase(Persistent):
    category = "game"
    subcat = None
    ignore_leading_articles = ["a", "an", "the"]
    
    @classmethod
    def guess(cls, file, info):
        if "basename" in file.flags:
            name = os.path.basename(file.pathname)
        else:
            name = file.pathname
        name = utils.decode_title_text(name)
        if info.mime.startswith("games/atari-8bit"):
            return Atari8bitScan(file, info)
        elif info.mime.startswith("games/atari-st"):
            return AtariSTScan(file, info)
        return GameScanBase(file, info)
    
    def __init__(self, file, info):
        self.play_date = None
        self.save_game = None
        self.position = 0
        self.init_common(file, info)
        self.title_key = self.calc_title_key(file, info)
    
    def __str__(self):
        return "%s/%s" % (self.category, self.subcat)
    
    def sort_key(self):
        """Return a 1-tuple:
        
        name
        """
        t = self.title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                t = t[len(a):] + ", %s" % t[0:len(article)]
                break
        return (t,)
    
    def init_common(self, file, info):
        self.title = self.calc_title(file, info)
    
    def calc_title_key(self, file, info):
        return utils.TitleKey(self.category, self.subcat, self.title, None)
    
    def calc_title(self, file, info):
        return os.path.basename(file.pathname)
    
    def has_saved_games(self):
        return False
    
    def get_saved_games(self):
        return []

class Atari8bitScan(GameScanBase):
    category = "game"
    subcat = "atari-8bit"

class AtariSTScan(GameScanBase):
    category = "game"
    subcat = "atari-st"


from ..filescan import MediaFile
MediaFile.register("MEDIA_GAME", GameScanBase)
