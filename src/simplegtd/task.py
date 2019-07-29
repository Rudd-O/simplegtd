import re

from gi.repository import GLib


# FIXME in lieu of using a CellRenderer for a task object,
# we will temporarily use this shit.
def markup_for(task_text):
    date_regex = re.compile("^([12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))$")
    list_regex = re.compile("^@[a-zA-Z0-9]")
    context_regex = re.compile("^@@[a-zA-Z0-9]")
    prio_regex = re.compile("^[(][A-Z][)]$")
    tag_regex = re.compile("^[+]")
    newtoks = []
    m = GLib.markup_escape_text
    for tok in task_text.split(" "):
        if date_regex.match(tok):
            # FIXME if date is overdue mark it up as red.
            newtoks.append("<span foreground='green'>%s</span>" % m(tok))
        elif context_regex.match(tok):
            newtoks.append("<span foreground='darkblue'>%s</span>" % m(tok))
        elif list_regex.match(tok):
            newtoks.append("<span foreground='darkgreen'>%s</span>" % m(tok))
        elif tag_regex.match(tok):
            newtoks.append("<span foreground='darkviolet'>%s</span>" % m(tok))
        elif prio_regex.match(tok):
            newtoks.append("<span foreground='chocolate'>%s</span>" % m(tok))
        else:
            newtoks.append(m(tok))
    new_text = " ".join(newtoks)
    if task_text.startswith("x "):
        new_text = "<span strikethrough='true' color='gray'>%s</span>" % new_text
    return new_text
