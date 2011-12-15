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
        menu = MenuItem(media.in_context_title)
        parent_menu.add(menu)
        return menu, False

    def add_movie_title_to_menu(self, movie_title, parent_menu):
        """Add MovieTitle object to menu

        """
        title_menu = MenuItem(movie_title.canonical_title, metadata=movie_title)
        parent_menu.add(title_menu)
        
        first_bonus = True
        for movie in movie_title.children:
            items = []
            if movie.is_bonus_feature():
                if first_bonus:
                    items.append(MenuItem("Bonus Features", enabled=False))
                    first_bonus = False
                submenu = MenuItem(movie.in_context_title, media=movie, action=movie.play)
                items.append(submenu)
                for item in self.get_movie_options(movie):
                    submenu.add(item)
            else:
                items.extend(self.get_movie_options(movie))
            for item in items:
                title_menu.add(item)
        return title_menu, True

    def get_movie_options(self, movie):
        items = []
        items.append(MenuItem(movie.in_context_title, enabled=False))
        items.append(MenuItem("Play (%s)" % movie.get_runtime(), media=movie, action=movie.play))
        items.append(MenuItem("Resume", media=movie, action=movie.resume, enabled=False))
        items.append(MenuItem("Audio Options", enabled=False))
        
        radio = []
        first = True
        for options in movie.get_audio_options():
            toggle = Toggle(options[1], state=first, radio=radio, index=options[0], action=movie.set_audio_options)
            # Note: radio list is being added to as we go; we're taking
            # advantage of argument passing by reference so that each
            # of the toggles will have the same radio list
            radio.append(toggle)
            items.append(toggle)
            first = False
        if radio:
            radio[0].initialize_action()
        items.append(MenuItem("Subtitles", enabled=False))
        
        radio = []
        first = True
        for options in movie.get_subtitle_options():
            toggle = Toggle(options[1], state=first, radio=radio, index=options[0], action=movie.set_subtitle_options)
            radio.append(toggle)
            items.append(toggle)
            first = False
        if radio:
            radio[0].initialize_action()
        return items

    def add_movie_options_to_menu(self, movie, parent_menu):
        """Add Movie (or SeriesEpisode) object to menu

        """
        title_menu = MenuItem(movie.in_context_title, metadata=movie)
        parent_menu.add(title_menu)
        
        items = self.get_movie_options(movie)
        for item in items:
            title_menu.add(item)
        return parent_menu, True
