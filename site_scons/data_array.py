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


import array
import os
import string

import SCons


def dataarray_action(target, source, env):
    sizBytesPerLine = int(env['DATAARRAY_BYTES_PER_LINE'])
    sizElement = int(env['DATAARRAY_ELEMENT_SIZE'])

    if sizBytesPerLine < 1:
        raise Exception('Invalid number of bytes per row! This value must be '
                        'greater than 0.')

    if sizElement == 1:
        strArrayFormat = 'B'
        strCTypeName = 'unsigned char'
        strDefaultArrayName = 'aucData'
    elif sizElement == 2:
        strArrayFormat = 'H'
        strCTypeName = 'unsigned short'
        strDefaultArrayName = 'ausData'
    elif sizElement == 4:
        strArrayFormat = 'I'
        strCTypeName = 'unsigned long'
        strDefaultArrayName = 'aulData'
    else:
        raise Exception('Invalid element size, must be 1, 2 or 4, but it '
                        'is %d' % sizElement)
    strPrintFormat = '0x%%0%dx' % (2 * sizElement)

    sizElementsPerLine = sizBytesPerLine / sizElement

    # Get the array name.
    if(
        (env['DATAARRAY_NAME'] is None) or (
            (not env['DATAARRAY_NAME'] is None) and
            len(env['DATAARRAY_NAME']) == 0
        )
    ):
        strArrayName = strDefaultArrayName
    else:
        strArrayName = env['DATAARRAY_NAME']

    # Read the complete input file in an array.
    sizFile = os.stat(source[0].get_path()).st_size
    if (sizFile % sizElement) != 0:
        raise Exception('The file size (%d) is no multiple of the selected '
                        'element size (%d).' % (sizFile, sizElement))
    sizArray = sizFile / sizElement

    atSourceData = array.array(strArrayFormat)
    tFileSource = open(source[0].get_path(), 'rb')
    atSourceData.fromfile(tFileSource, sizArray)

    tFileTarget = open(target[0].get_path(), 'wt')
    tFileTarget.write('const %s %s[%d] =\n' % (
        strCTypeName,
        strArrayName,
        sizArray
    ))
    tFileTarget.write('{\n')
    sizElementCnt = 0
    sizElementLineCnt = 0
    strDump = ''
    for tData in atSourceData:
        # Print the current offset at the start of each line.
        if sizElementLineCnt == 0:
            strDump = '\t'

        strDump += strPrintFormat % tData
        sizElementCnt += 1
        sizElementLineCnt += 1

        if sizElementCnt < sizArray:
            strDump += ', '

        if sizElementLineCnt == sizElementsPerLine:
            strDump += '\n'
            tFileTarget.write(strDump)
            sizElementLineCnt = 0
    if sizElementLineCnt > 0:
        strDump += '\n'
        tFileTarget.write(strDump)
    tFileTarget.write('};\n')
    tFileTarget.close()

    # Write the header file.
    strDefineName = os.path.basename(target[1].get_path()).upper().replace(
        '.',
        '_'
    )
    file_target = open(target[1].get_path(), 'wt')
    file_target.write('#ifndef __%s__\n' % strDefineName)
    file_target.write('#define __%s__\n' % strDefineName)
    file_target.write('\n')
    file_target.write('#ifdef __cplusplus\n')
    file_target.write('extern "C" {\n')
    file_target.write('#endif\n')
    file_target.write('\n')
    file_target.write('extern const %s %s[%d];\n' % (
        strCTypeName,
        strArrayName,
        sizArray
    ))
    file_target.write('\n')
    file_target.write('#ifdef __cplusplus\n')
    file_target.write('}\n')
    file_target.write('#endif\n')
    file_target.write('\n')
    file_target.write('#endif  /* __%s__ */\n' % strDefineName)
    file_target.write('\n')
    file_target.close()

    return 0


def dataarray_emitter(target, source, env):
    # Make the target depend on the parameter.
    env.Depends(target, SCons.Node.Python.Value(
        env['DATAARRAY_NAME']
    ))
    env.Depends(target, SCons.Node.Python.Value(
        env['DATAARRAY_BYTES_PER_LINE']
    ))
    env.Depends(target, SCons.Node.Python.Value(
        env['DATAARRAY_ELEMENT_SIZE']
    ))

    # Add the header file to the list of targets.
    strBase, strOldExt = os.path.splitext(target[0].get_path())
    strHeader = strBase + '.h'
    target.append(strHeader)

    return target, source


def dataarray_string(target, source, env):
    return 'DataArray %s / .h' % target[0].get_path()


def ApplyToEnv(env):
    # Sanity checks.
    if array.array('B').itemsize != 1:
        raise Exception('The item size of an array of type "B" is not 8bit. '
                        'This is an internal error or the bootblock builder.')
    if array.array('H').itemsize != 2:
        raise Exception('The item size of an array of type "H" is not 16bit. '
                        'This is an internal error or the bootblock builder.')
    if array.array('I').itemsize != 4:
        raise Exception('The item size of an array of type "I" is not 32bit. '
                        'This is an internal error or the bootblock builder.')

    # ------------------------------------------------------------------------
    #
    # Add dataarray builder.
    #
    env['DATAARRAY_NAME'] = ''
    env['DATAARRAY_BYTES_PER_LINE'] = 16
    env['DATAARRAY_ELEMENT_SIZE'] = 1

    dataarray_act = SCons.Action.Action(dataarray_action, dataarray_string)
    dataarray_bld = SCons.Script.Builder(
        action=dataarray_act,
        emitter=dataarray_emitter,
        suffix='.c',
        single_source=1
    )

    env['BUILDERS']['DataArray'] = dataarray_bld
