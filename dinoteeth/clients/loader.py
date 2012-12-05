import os

class Client(object):
    category_map = {}
    
    @classmethod
    def get_class(cls, cat, subcat):
        try:
            subcat_map = cls.category_map[cat]
        except KeyError:
            raise RuntimeError("Metadata category %s not known" % cat)
        if subcat not in subcat_map:
            subcat = "*"
        try:
            baseclass = subcat_map[subcat]
        except KeyError:
            raise RuntimeError("Metadata category %s/%s not known" % (cat, subcat))
        return baseclass

    @classmethod
    def register(cls, cat, subcat, baseclass):
        if cat not in cls.category_map:
            cls.category_map[cat] = {}
        if subcat is None:
            subcat = "*"
        cls.category_map[cat][subcat] = baseclass

    @classmethod
    def get_loader(cls, obj):
        if hasattr(obj, "scan") and obj.scan is not None:
            cat = obj.scan.title_key.category
            subcat = obj.scan.title_key.subcategory
        elif hasattr(obj, "media_category") and obj.media_category is not None:
            cat = obj.media_category
            subcat = obj.media_subcategory
        else:
            cat = obj.category
            subcat = obj.subcategory
        baseclass = cls.get_class(cat, subcat)
        return baseclass

    def __init__(self, settings):
        self.settings = settings
    
    def play(self, media_file, resume_at=0.0, **kwargs):
        pass
