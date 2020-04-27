#!/usr/bin/python3

import glob
from setuptools import setup
import os
import platform

dir = os.path.dirname(__file__)
path_to_main_file = os.path.join(dir, "src/simplegtd/__init__.py")
path_to_readme = os.path.join(dir, "README.md")
for line in open(path_to_main_file):
	if line.startswith('__version__'):
		version = line.split()[-1].strip("'").strip('"')
		break
else:
	raise ValueError('"__version__" not found in "src/simplegtd/__init__.py"')
readme = open(path_to_readme).read(-1)

classifiers = [
'Development Status :: 3 - Alpha',
'Environment :: X11 Applications :: GTK',
'Intended Audience :: End Users/Desktop',
'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
'Operating System :: POSIX :: Linux',
'Programming Language :: Python :: 3 :: Only',
'Programming Language :: Python :: 3.6',
'Topic :: Office/Business :: Scheduling',
'Topic :: Office/Business :: Groupware',
]

programs = [
    "simplegtd",
]

ui_files = [
    "shortcuts-window.ui",
]

icons = [
    "simplegtd.svg",
]

# Don't write to /usr/share/applications on OS X to work around the
# 'System Integrity Protection'.
g = lambda p: os.path.join(os.path.dirname(__file__), p)
data_files = [
	("/usr/share/applications", [g("applications/%s.desktop") % p for p in programs]),
	("/usr/share/icons", [g("icons/%s") % p for p in icons]),
	("/usr/share/simplegtd", [g("data/%s") % p for p in ui_files]),
] if platform.system() != 'Darwin' else []

setup(
	name='simplegtd',
	version=version,
	description='Manage your to-do list using the Getting Things Done system.',
	long_description = readme,
	author='Manuel Amador (Rudd-O)',
	author_email='rudd-o@rudd-o.com',
	license="GPLv3+",
	url='https://pypi.org/project/simplegtd/',
	package_dir=dict([
                    ("simplegtd", "src/simplegtd"),
					]),
	classifiers = classifiers,
	packages=["simplegtd", "simplegtd.libwhiz", "simplegtd.models"],
	data_files = data_files,
	scripts=["bin/%s" % p for p in programs],
	keywords="gtd getting things done TODO.TXT",
	zip_safe=False,
	install_requires=['pyxdg'],
)
