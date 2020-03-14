# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
#   Copyright (C) 2012 by Christoph Thelen                                #
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
import SCons.Node.FS
import SCons.Script


# ---------------------------------------------------------------------------
# Usage:
#
# tArc = env.ArchiveList('zip')
# tArc.AddFiles('path/',          FileNode,
#                                 NodeList)
# tArc.AddFiles('another/path/', 'filename')
# env.Archive('archive.zip', None, ARCHIVE_CONTENTS=tArc)
#
# ---------------------------------------------------------------------------

class ArchiveBuildInformation:
    def __init__(self, strArchiveType):
        self.strArchiveType = strArchiveType
        self.atContents = dict({})

    def AddFiles(self, strPath, *args):
        # Is the path already defined?
        if strPath not in self.atContents:
            # No -> create the entry.
            self.atContents[strPath] = []

        # Get a shortcut to the destination list.
        aDst = self.atContents[strPath]

        # Loop over all other arguments.
        for iCnt, tObj in enumerate(args):
            if isinstance(tObj, str) is True:
                aDst.append(SCons.Script.File(tObj))
            elif isinstance(tObj, SCons.Node.NodeList) is True:
                for tNodeObj in tObj:
                    aDst.append(tNodeObj)
            elif isinstance(tObj, SCons.Node.FS.Base) is True:
                aDst.append(tObj)
            else:
                print(tObj)
                raise Exception('Argument %d has an invalid type!' % iCnt+2)

    def getAllSourceFiles(self):
        # Return a list with all source files.
        return self.atContents.values()

    def getAllPathFilePairs(self):
        # Return a list with
        atPathFilePairs = []
        for strPath, atFileList in self.atContents.iteritems():
            for tObj in atFileList:
                atPathFilePairs.append([strPath, tObj])
        return atPathFilePairs

    def writeArchive(self, strTargetPath):
        if self.strArchiveType == 'zip':
            # Create the target archive. This trucates an existing file.
            tZipFile = zipfile.ZipFile(
                strTargetPath,
                'w',
                zipfile.ZIP_DEFLATED
            )
            # Add all source files.
            for strPath, atFileList in self.atContents.iteritems():
                for tObj in atFileList:
                    strSourceName = tObj.get_path()
                    strArchiveName = os.path.join(
                        strPath,
                        os.path.basename(strSourceName)
                    )
                    tZipFile.write(strSourceName, strArchiveName)
            # Close the archive.
            tZipFile.close()
        else:
            raise Exception(
                'Unsupported archive format: %s' %
                self.strArchiveType
            )


def ArchiveList(env, *args):
    # The number of optional arguments must be 0 or 1.
    if len(args) == 0:
        strArchiveType = 'zip'
    elif len(args) == 1:
        if isinstance(args[0], str) is True:
            strArchiveType = args[0]
        else:
            raise Exception('Invalid arument type. It must be string.')
    else:
        raise Exception(
            'Invalid number of optional arguments: %d. Must be 0 or 1.' %
            len(args)
        )

    # Create the Archive object.
    return ArchiveBuildInformation(strArchiveType)


# ---------------------------------------------------------------------------


def archive_action(target, source, env):
    if env['ARCHIVE_CONTENTS'] is not None:
        tArchiveContents = env['ARCHIVE_CONTENTS']
        tArchiveContents.writeArchive(target[0].get_path())

    return None


def archive_emitter(target, source, env):
    # Loop over all elements in the archive.

    if env['ARCHIVE_CONTENTS'] is not None:
        tArchiveContents = env['ARCHIVE_CONTENTS']

        # Get all input files and make the target depend on them.
        tSrcFiles = tArchiveContents.getAllSourceFiles()
        env.Depends(target, tSrcFiles)
        source.extend(tSrcFiles)

        # Each input file has a path in the zip archive. Get the all tuples of
        # the path and file.
        atPathFiles = tArchiveContents.getAllPathFilePairs()
        atDepends = []
        for tTuple in atPathFiles:
            atDepends.append('%s:%s' % (tTuple[0], tTuple[1].get_path()))

        # Sort the dependencies.
        atDepends.sort()

        for strDepends in atDepends:
            env.Depends(target, SCons.Node.Python.Value(strDepends))

    return target, source


def archive_string(target, source, env):
    return 'Archive %s' % target[0].get_path()


# ---------------------------------------------------------------------------


def ApplyToEnv(env):
    archive_act = SCons.Action.Action(archive_action, archive_string)
    archive_bld = SCons.Script.Builder(
        action=archive_act,
        emitter=archive_emitter
    )
    env['BUILDERS']['Archive'] = archive_bld
    env.AddMethod(ArchiveList, "ArchiveList")
