import os, time, subprocess

from .. import settings


class Client(object):
    prog_map = {}
    
    @classmethod
    def get_class(cls, cat, subcat):
        progname = None
        for s in [subcat, "*"]:
            scantype = cls.get_scantype(cat, s)
            if scantype in settings.client_progs:
                prog_name = settings.client_progs[scantype]
        if prog_name is None:
            raise RuntimeError("Metadata category %s/%s not known" % (cat, subcat))
        if prog_name in cls.prog_map:
            return cls.prog_map[prog_name], prog_name
        
        # If there's no specific program handler, assume there's nothing
        # specific about the program and the generic handler will work.
        return cls, prog_name

    @classmethod
    def register(cls, prog_name, baseclass):
        cls.prog_map[prog_name] = baseclass

    @classmethod
    def get_scantype(cls, cat, subcat):
        scantype = "%s/%s" % (cat, subcat)
        return scantype

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
        baseclass, prog_name = cls.get_class(cat, subcat)
        return baseclass(prog_name)

    def __init__(self, prog_name):
        self.settings = settings
        self.prog_name = prog_name
    
    def get_prog_path(self):
        return self.prog_name
    
    def get_default_args(self):
        return settings.client_args.get(self.prog_name, "").split()
    
    def get_args(self, path):
        args = []
        prog = self.get_prog_path()
        args.append(prog)
        opts = self.get_default_args()
        args.extend(opts)
        
        root, ext = os.path.splitext(path)
        # do something with path if desired
        
        args.append(path)
        return args
    
    def play(self, media_file, resume_at=0.0, **kwargs):
        args = self.get_args(media_file.pathname)
        print args
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            print("stdout: %s" % stdout)
        if stderr:
            print("stderr: %s" % stderr)
        
        self.handle_save(stdout, stderr, **kwargs)
    
    def handle_save(self, stdout, stderr, **kwargs):
        pass
