#!/usr/bin/env python2.6

# Application start and main window for media player

import sys

from config import setup

class RendererFactory(object):
    @classmethod
    def get_layout(cls, window, margins, cfg):
        import view
        return view.MenuDetail2ColumnLayout(window, margins, cfg, cls)
    
    @classmethod
    def get_title_renderer(cls, window, box, cfg):
        import view
        return view.TitleRenderer(window, box, cfg)

    @classmethod
    def get_menu_renderer(cls, window, box, cfg):
        import view
        return view.VerticalMenuRenderer(window, box, cfg)

    @classmethod
    def get_detail_renderer(cls, window, box, cfg):
        import view
        return view.DetailRenderer(window, box, cfg)
    
def run():
    try:
        cfg = setup(sys.argv)
    except Exception, e:
        print "Startup failure: %s" % e
        import traceback
        traceback.print_exc()
        return
    window = cfg.get_main_window(RendererFactory)
    try:
        window.run()
    except Exception, e:
        import traceback
        traceback.print_exc()
        
        print "Halting threads..."
        cfg.do_shutdown_tasks()

def run_monitor():
    try:
        cfg = setup(sys.argv)
    except Exception, e:
        print "Startup failure: %s" % e
        import traceback
        traceback.print_exc()
        return
    cfg.start_update_monitor()
