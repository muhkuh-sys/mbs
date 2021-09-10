# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
#   Copyright (C) 2010 by Christoph Thelen                                #
#   doc_bacardi@users.sourceforge.net                                     #
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
#   This program is distributed in the hope that it will be useful,       #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#   GNU General Public License for more details.                          #
#                                                                         #
#   You should have received a copy of the GNU General Public License     #
#   along with this program; if not, write to the                         #
#   Free Software Foundation, Inc.,                                       #
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
# ----------------------------------------------------------------------- #


import os
import os.path
import subprocess
import sys

import clean_orphaned_pyc
import configuration
import filter
import install

iMinimumInterpreterVersion_maj = 2
iMinimumInterpreterVersion_min = 6

iMinimumInterpreterVersion_hex = (
    (iMinimumInterpreterVersion_maj << 24) |
    (iMinimumInterpreterVersion_min << 16)
)
if sys.hexversion < iMinimumInterpreterVersion_hex:
    sys.exit(
        'The setup script needs at least python %d.%d to run. '
        'Please update!' % (
            iMinimumInterpreterVersion_maj,
            iMinimumInterpreterVersion_min
        )
    )


def get_tool_path(aCfg, aTool):
    return os.path.join(
        aCfg['depack_path'],
        aTool['group'],
        aTool['name'],
        '%s-%s' % (aTool['name'], aTool['version'])
    )


aCfg = configuration.create()
configuration.read_user_config('~/.mbs.xml', aCfg)
configuration.read_project_config('setup.xml', aCfg)


# Create the folders.
if os.path.isdir(aCfg['marker_path']) is False:
    os.makedirs(aCfg['marker_path'])
if os.path.isdir(aCfg['repository_path']) is False:
    os.makedirs(aCfg['repository_path'])


# Install Scons.
install.process_package(aCfg, aCfg['scons'])
aToolScons = aCfg['scons']
aCfg['scons_path'] = os.path.join(get_tool_path(aCfg, aToolScons), 'scons.py')


# Install all other tools.
for aTool in aCfg['tools']:
    install.process_package(aCfg, aTool)


# Filter the files.
filter.apply(aCfg)


# Clean all orphaned ".pyc" files in the project. Be verbose and really delete
# the files.
# pyc files explanation and release python version of __pycache__:
# https://stackoverflow.com/questions/16869024/what-is-pycache
# https://docs.python.org/3/whatsnew/3.2.html?highlight=__pycache__#pep-3147-pyc-repository-directories
#
# Why not running without source file for python 3.2 and higher:
# https://stackoverflow.com/questions/25172773/running-without-python-source-files-in-python-3-4
# https://www.python.org/dev/peps/pep-3147/#case-3-pycache-foo-magic-pyc-with-no-source
#
# Only if the python Version is lower than 3.2
# https://docs.python.org/3/library/sys.html
if sys.version_info.major == 3 and sys.version_info.minor >= 2:
	print("It is not necessary to clean up .pyc files for python versions higher or equal to 3.2 .")
else:
	clean_orphaned_pyc.cleanup(os.getcwd(), True, False)


# Run Scons (use aCfg['scons'] to get the path. All archives *must* create a
# folder with the name '%s-%s'%(strName,strVersion) and have a 'scons.py'
# there.
print('Running scons (%s)' % aCfg['scons_path'])
sys.stdout.flush()
sys.stderr.flush()
astrArguments = [sys.executable, aCfg['scons_path']]
astrArguments.append('--site-dir=%s' % os.path.abspath('targets/site_scons'))
astrArguments.append('--include-dir=%s' % os.path.abspath('site_scons'))
astrArguments.append('--include-dir=%s' % os.path.abspath('mbs/site_scons'))
astrArguments.extend(sys.argv[1:])
sys.exit(subprocess.call(astrArguments))
