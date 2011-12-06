import os, sys, glob, bisect

from model import MenuItem, Toggle

class MenuTheme(object):
    def add_menu_hierarchy(self, menu, media_hierarchy):
        """Convert a hierarchy of MediaObjects to a set of MenuItems
        
        The hierarchy of MediaObjects resulting from a call to
        MediaResults.hierarchy gets converted here to a set of menus and
        submenus for display by the UI.
        """
        children = media_hierarchy.children
        for media in children:
            submenu, handled_children = media.add_to_menu(self, menu)
            if not handled_children and media.children:
                self.add_menu_hierarchy(submenu, media)

    def add_simple_menu(self, media, parent_menu):
        """Default menu handler that simply adds the title and doesn't process
        any children.
        """
        menu = MenuItem(media.canonical_title)
        parent_menu.add(menu)
        return menu, False

    def add_movie_title_to_menu(self, movie_title, parent_menu):
        """Add MovieTitle object to menu

        """
        title_menu = MenuItem(movie_title.canonical_title)
        parent_menu.add(title_menu)
        
        first_bonus = True
        for movie in movie_title.children:
            items = []
            if movie.is_bonus_feature():
                if first_bonus:
                    items.append(MenuItem("Bonus Features", enabled=False))
                    first_bonus = False
                items.append(MenuItem(movie.in_context_title, media=movie))
            else:
                items.append(MenuItem(movie.in_context_title, enabled=False))
                items.append(MenuItem("Play", media=movie))
                items.append(MenuItem("Resume", media=movie, enabled=False))
                items.append(MenuItem("Audio Options", enabled=False))
                
                radio = []
                first = True
                for options in movie.get_audio_options():
                    toggle = Toggle(options[1], state=first, radio=radio, user_data=options[0])
                    # Note: radio list is being added to as we go; we're taking
                    # advantage of argument passing by reference so that each
                    # of the toggles will have the same radio list
                    radio.append(toggle)
                    items.append(toggle)
                    first = False
                items.append(MenuItem("Subtitles", enabled=False))
                
                radio = []
                first = True
                for options in movie.get_subtitle_options():
                    toggle = Toggle(options[1], state=first, radio=radio, user_data=options[0])
                    radio.append(toggle)
                    items.append(toggle)
                    first = False
            for item in items:
                title_menu.add(item)
        return title_menu, True
