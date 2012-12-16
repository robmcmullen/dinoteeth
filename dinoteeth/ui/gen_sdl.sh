#!/bin/sh

ctypesgen.py -L/usr/lib -I/usr/include/SDL -lSDL /usr/include/SDL/SDL.h /usr/include/SDL/SDL_quit.h /usr/include/SDL/SDL_key* /usr/include/SDL/SDL_config.h /usr/include/SDL/SDL_video.h /usr/include/SDL/SDL_events.h /usr/include/SDL/SDL_timer.h /usr/include/SDL/SDL_mouse.h -o SDL.py
ctypesgen.py -L/usr/lib -I/usr/include/SDL -lSDL_Pango /usr/include/SDL_Pango.h -o SDL_Pango.py
ctypesgen.py -L/usr/lib -I/usr/include/SDL -lSDL_image /usr/include/SDL/SDL_image.h -o SDL_Image.py
ctypesgen.py -L/usr/lib -I/usr/include/SDL -lSDL_gfx /usr/include/SDL/SDL_gfxPrimitives.h -o SDL_gfx.py

