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
import difflib

import SCons


def diff_action(target, source, env):
    # Get the folder with the original sources.
    strOrgFolder = env['DIFF_ORIGINAL_FOLDER']
    strPatchedFolder = env['DIFF_PATCHED_FOLDER']

    # Collect the complete diff in this file.
    tFileTarget = open(target[0].get_path(), 'w')

    # Loop over all sources.
    for tSource in source:
        strSourcePath = tSource.get_path()

        if strOrgFolder is None:
            tSrcFileA = None
            aSourceA = []
        else:
            tSrcFileA = open(os.path.join(strOrgFolder, strSourcePath), 'r')
            aSourceA = tSrcFileA.readlines()

        tSrcFileB = open(strSourcePath, 'r')
        aSourceB = tSrcFileB.readlines()

        strFileName = os.path.join(strPatchedFolder, strSourcePath)

        for strLine in difflib.unified_diff(
            aSourceA,
            aSourceB,
            fromfile=strFileName,
            tofile=strFileName
        ):
            tFileTarget.write(strLine)

        if tSrcFileA is not None:
            tSrcFileA.close()
        tSrcFileB.close()

    tFileTarget.close()

    return 0


def diff_emitter(target, source, env):
    # Make the target depend on the parameter.
    env.Depends(target, SCons.Node.Python.Value(env['DIFF_ORIGINAL_FOLDER']))
    env.Depends(target, SCons.Node.Python.Value(env['DIFF_PATCHED_FOLDER']))

    return target, source


def diff_string(target, source, env):
    return 'Diff %s' % target[0].get_path()


def ApplyToEnv(env):
    # ------------------------------------------------------------------------
    #
    # Add diff builder.
    #
    env['DIFF_ORIGINAL_FOLDER'] = None
    env['DIFF_PATCHED_FOLDER'] = ''

    diff_act = SCons.Action.Action(diff_action, diff_string)
    diff_bld = SCons.Script.Builder(
        action=diff_act,
        emitter=diff_emitter,
        suffix='.diff'
    )
    env['BUILDERS']['Diff'] = diff_bld
