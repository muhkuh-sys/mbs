# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
#   Copyright (C) 2011 by Christoph Thelen                                #
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
import zipfile

import SCons


def zip_action(target, source, env):
    # Create the target archive. This trucates an existing file.
    tZipFile = zipfile.ZipFile(target[0].get_path(), 'w', zipfile.ZIP_DEFLATED)

    if 'ZIP_PATH_TRANSLATE' in env:
        aTranslate = env['ZIP_PATH_TRANSLATE']
    else:
        aTranslate = dict({})

    # Add all source files.
    for tSource in source:
        strFileName = tSource.get_path()

        if tSource in aTranslate:
            strDstPath = os.path.join(
                aTranslate[tSource],
                os.path.basename(strFileName)
            )
        else:
            strDstPath = os.path.basename(strFileName)

        tZipFile.write(strFileName, strDstPath)

    # Close the archive.
    tZipFile.close()

    return None


def zip_emitter(target, source, env):
    # The target depends on all files in the TESTS list.

    # Loop over all paths for a test.
    if env['ZIP_PATH_TRANSLATE'] is None:
        aTranslate = []

        for (tFile, strPath) in env['ZIP_PATH_TRANSLATE'].items():
            aTranslate.append('%s:%s' % (tFile.get_path(), strPath))

        for strDep in sorted(aTranslate):
            # Depend on the combination of the file and the install dir.
            env.Depends(target, SCons.Node.Python.Value(strDep))

    return target, source


def zip_string(target, source, env):
    return 'FlexZip %s' % target[0].get_path()


# ---------------------------------------------------------------------------


def ApplyToEnv(env):
    env['ZIP_PATH_TRANSLATE'] = dict({})
    zip_act = SCons.Action.Action(zip_action, zip_string)
    zip_bld = SCons.Script.Builder(
        action=zip_act,
        emitter=zip_emitter,
        suffix='.zip'
    )
    env['BUILDERS']['FlexZip'] = zip_bld
