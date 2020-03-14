# This utility recursively scans a folder and looks for ".pyc" files which do
# not have a matching ".py" file anymore.
#
# This situation occurs when the Muhkuh build system is restructured in a way
# that old builders are removed or complex builders are migrated from one big
# files to several files in a subfolder (like the HBOOT image compiler).
#
# A GIT "pull" operation will just apply the changes to the ".py" file, but
# the old ".pyc" files are still there and block the new functionality.

import os
import os.path


def cleanup(strPath, fVerbose=True, fDryRun=True):
    if fVerbose is True:
        print('Scanning "%s" for orphaned ".pyc" files.' % (strPath))

    # Scan the selected path recursively for all ".py" and ".pyc" files.
    astrPy = set()
    astrPyc = set()
    for strRoot, astrDirs, astrFiles in os.walk(strPath):
        # Loop over all files in the current directory.
        for strFile in astrFiles:
            # Get the extension of the file.
            strBase, strExt = os.path.splitext(strFile)

            # Get the absolute path without the extension.
            strAbsBase = os.path.join(strRoot, strBase)

            # Keep all ".py" files in astrPy, keep all ".pyc" files in astrPyc.
            if strExt == '.py':
                astrPy.add(strAbsBase)
            elif strExt == '.pyc':
                astrPyc.add(strAbsBase)

    # Find the entries in astrPyc which are not in astrPy.
    atDiff = astrPyc.difference(astrPy)

    # Process all files to delete.
    iOrphanedFiles = len(atDiff)
    if iOrphanedFiles == 0:
        if fVerbose is True:
            print('No oprhaned ".pyc" files.')
    else:
        if fVerbose is True:
            strPlural = ''
            if iOrphanedFiles > 1:
                strPlural = 's'
            print('%d orphaned file%s found:' % (iOrphanedFiles, strPlural))

        strAction = 'Found'
        if fDryRun is not True:
            strAction = 'Deleting'

        for strAbsBase in atDiff:
            strAbs = strAbsBase + '.pyc'
            if fVerbose is True:
                print('  %s %s' % (strAction, strAbs))

            if fDryRun is not True:
                os.remove(strAbs)
