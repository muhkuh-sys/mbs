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

import SCons.Script


def hexdump_action(target, source, env):
    sizSkip = int(env['HEXDUMP_SKIPBYTES'], 0)
    sizMax = int(env['HEXDUMP_MAXSIZE'], 0)

    # Read the source data into an array.
    strSourceData = source[0].get_contents()
    # A 0 for the maximum size means all data.
    if sizMax == 0:
        sizMax = len(strSourceData)
    # Limit the data to the requested part.
    strSourceData = strSourceData[sizSkip:(sizSkip + sizMax)]

    iElemSize = float(env['HEXDUMP_ELEMENT_SIZE'])
    if iElemSize == 1:
        strArrayFormat = 'B'
    elif iElemSize == 2:
        strArrayFormat = 'H'
    elif iElemSize == 4 or iElemSize == 4.5:
        strArrayFormat = 'I'
    else:
        raise Exception('Invalid element size, must be 1, 2 4 or 4.5, '
                        'but it is %d' % iElemSize)

    atSourceData = array.array(strArrayFormat)
    atSourceData.fromstring(strSourceData)

    if iElemSize == 4.5:
        file_target_lo = open(target[0].get_path(), 'wt')
        file_target_hi = open(target[1].get_path(), 'wt')

        # Loop over all elements.
        for tElement in atSourceData:
            file_target_lo.write(' %04x\n' % (tElement & 0xffff))
            file_target_hi.write(' %04x\n' % (tElement >> 16))

        # Close the output file.
        file_target_lo.close()
        file_target_hi.close()

    else:
        file_target = open(target[0].get_path(), 'w')

        strPrintFormat = ' %%0%dx\n' % (iElemSize * 2)

        # Loop over all elements.
        for tElement in atSourceData:
            file_target.write(strPrintFormat % tElement)

        # Close the output file.
        file_target.close()

    return 0


def hexdump_emitter(target, source, env):
    # Get the element size.
    sizElement = float(env['HEXDUMP_ELEMENT_SIZE'])

    # Make the target depend on the parameter.
    env.Depends(target, SCons.Node.Python.Value(sizElement))
    env.Depends(target, SCons.Node.Python.Value(env['HEXDUMP_SKIPBYTES']))

    # The element size of 4.5 is special. It cuts the 32 bit words in 2 words
    # with 16 bits each.
    # The files are named after the first target.
    if sizElement == 4.5:
        strPath, strExt = os.path.splitext(target[0].get_path())
        target = [
            SCons.Script.File(strPath + '_lo' + strExt),
            SCons.Script.File(strPath + '_hi' + strExt)
        ]

    return target, source


def hexdump_string(target, source, env):
    return 'HexDump %s' % ', '.join([t.get_path() for t in target])


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
    # Add hexdump builder.
    #
    env['HEXDUMP_ELEMENT_SIZE'] = 4
    env['HEXDUMP_SKIPBYTES'] = '0'
    env['HEXDUMP_MAXSIZE'] = '0'

    hexdump_act = SCons.Action.Action(hexdump_action, hexdump_string)
    hexdump_bld = SCons.Script.Builder(
        action=hexdump_act,
        emitter=hexdump_emitter,
        suffix='.hex',
        single_source=1
    )
    env['BUILDERS']['HexDump'] = hexdump_bld
