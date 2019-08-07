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
'Topic :: Office/Business :: Financial :: Accounting',
]

programs = [
    "simplegtd",
]

ui_files = [
    "shortcuts-window.ui",
]

# https://github.com/Rudd-O/ledgerhelpers/issues/3
# Don't write to /usr/share/applications on OS X to work around the
# 'System Integrity Protection'.
data_files = [
	("/usr/share/applications", ["applications/%s.desktop" % p for p in programs]),
	("/usr/share/simplegtd", ["data/%s" % p for p in ui_files]),
] if platform.system() != 'Darwin' else []

setup(
	name='simplegtd',
	version=version,
	description='An extremely simple, bare-bones GTD app',
	long_description = readme,
	author='Manuel Amador (Rudd-O)',
	author_email='rudd-o@rudd-o.com',
	license="GPLv3+",
	url='http://github.com/Rudd-O/simplegtd',
	package_dir=dict([
                    ("simplegtd", "src/simplegtd"),
					]),
	classifiers = classifiers,
	packages=["simplegtd"],
	data_files = data_files,
	scripts=["bin/%s" % p for p in programs],
	keywords="gtd getting things done",
	zip_safe=False,
	install_requires=['xdg'],
)
