import __builtin__

# Implement fake gettext to handle markup conversion if needed by the choice of
# ui.  Will be replaced (or augmented if i18n ever happens) by the MainWindow
# subclass of the chosen ui.
def noop_translate(string):
    return string

__builtin__._ = noop_translate
