'''See https://wiki.gnome.org/HowDoI/CustomStyle'''

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk


__css_adjusted = {}


def add(css):
    # Must only ever be called at runtime, not at import time.
    # See https://github.com/GNOME/gtk/blob/master/gtk/theme/Adwaita/_colors-public.scss
    global __css_adjusted
    if css not in __css_adjusted:
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    __css_adjusted[css] = True
