import os, sys, glob
import pyglet

def decode_title_text(text):
    return text.replace('_n_',' & ').replace('-s_','\'s ').replace('-t_','\'t ').replace('-m_','\'m ').replace('_',' ')

def shell_escape_path(path):
    escape_chars = [' ', '&', '(', ')']
    escaped_path = path
    for c in escape_chars: escaped_path = escaped_path.replace(c, "\\"+c)
    return escaped_path

def time_format(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)
