# Simple GTD: manage your TODO.txt

Simple GTD lets you manage your to-do list using the Getting Things Done system.

Skip below for usage and installation instructions.

## Features

**Sync-ready and sync-friendly**

While Simple GTD does not have any built-in sync features -- and has no plans to gain them -- it supports any sync tool you want to use, from Git to Syncthing to Dropbox.  Incoming changes to your to-do file are reflected in the user interface immediately.  The author has verified that syncing `todo.txt` to and from Simpletask Cloudless works perfectly (using Syncthing as the sync mechanism).

The algorithm used to persist and detect state changes in the to-do file is robust and efficient.  When Simple GTD detects external changes to your to-do file, only the portions of the file that changed are reloaded.  When you make changes to your to-do file in Simple GTD, Simple GTD saves the changes immediately, letting your sync program do its job right away.

**Keyboard- and mouse-friendly**

Entering new tasks and managing existing tasks with Simple GTD is quick and easy -- a single keystroke to add a task, and a single keystroke to edit an existing task.  Most of the standard shortcut keys you've learned work exactly as intended.

**Fast**

The program is consciously developed to reduce the overhead of common operations like inserting / rearranging / filtering your to-do lists.

**Multi-lists**

Unlike most to-do apps, you can manage multiple lists with Simple GTD.  Exiting the app and reopening the app again will open all lists you had open before.  Even window sizes are remembered per list, so short and long lists won't be a chore to manage.

## Usage

The application is fairly simple to use.  When you start it, an empty window will pop up.  Click on the *Help* icon in the header bar to see the shortcut keys you can use to manage your tasks.  The standard keyboard shortcuts will work well.

By default, the application will store your `todo.txt` file in its hidden data directory (on Linux, `~/.local/share/simplegtd/`) within your home folder.  You can, however, change that -- use the header bar Open icon to select / create a to-do file of your choice anywhere you want.  Simple GTD will then open a new window with the file.  Now close the other window -- Simple GTD will now remember which files you have opened.

The application will remember multiple windows with different files open as well.  If you quit the application (using Quit in the toolbar or the keyboard combination) instead of closing windows one-by-one, next time you run it, Simple GTD will reopen the files you'd had open first.

## Installation

### Requirements

Ensure your system has the necessary requirements:

* Python 3
* GTK+ 3
* the GTK+ Python 3 bindings (pygobject3)
* the PyXDG Python 3 module (pyxdg)
* libhandy 1.x

You can now install it or run it from source.

### Install

#### From PyPI

1. `pip3 install --user simplegtd`
2. Ensure the `simplegtd` entry point script is in your `PATH`.
3. Copy the files in your Python's `site-packages/simplegtd/data/applications` to your `~/.local/share/applications`.
4. Copy the files in your Python's `site-packages/simplegtd/data/icons` to your `~/.local/share/icons`.

#### From RPM

Packages for Fedora named `simplegtd` are available at the appropriate subdirectory within https://repo.rudd-o.com/ .

### Run directly from source

```
PYTHONPATH=src python3 src/simplegtd/__init__.py
```
