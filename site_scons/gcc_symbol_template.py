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


import binascii
import codecs
import elf_support
import string

import SCons.Action
import SCons.Script


def gccsymboltemplate_action(target, source, env):
    # Get the source path.
    strSourcePath = source[0].get_path()

    # Get the symbol table from the elf.
    atSymbols = elf_support.get_symbol_table(env, strSourcePath)

    # Get the macros from the ELF file.
    atElfMacros = elf_support.get_macro_definitions(env, strSourcePath)
    atSymbols.update(atElfMacros)

    # Get the debug information from the ELF file.
    atElfDebugSymbols = elf_support.get_debug_symbols(env, strSourcePath)
    atSymbols.update(atElfDebugSymbols)

    # Read the template.
    tTemplateFilename = env['GCCSYMBOLTEMPLATE_TEMPLATE']
    if isinstance(tTemplateFilename, str):
        strTemplateFilename = tTemplateFilename
    else:
        # Assume this is a file.
        strTemplateFilename = tTemplateFilename.get_path()
    tFile = codecs.open(strTemplateFilename, 'r')
    strTemplate = tFile.read()
    tFile.close()

    # Search and replace the special "%EXECUTION_ADDRESS%".
    strExecutionAddress = '0x%08x' % elf_support.get_exec_address(
        env,
        strSourcePath
    )
    strTemplate = strTemplate.replace(
        '${%EXECUTION_ADDRESS%}',
        strExecutionAddress
    )

    # Search and replace the special "%LOAD_ADDRESS%".
    atSegments = elf_support.get_segment_table(env, strSourcePath)
    strLoadAddress = '0x%08x' % elf_support.get_load_address(atSegments)
    strTemplate = strTemplate.replace(
        '${%LOAD_ADDRESS%}',
        strLoadAddress
    )

    # Search and replace the special "%PROGRAM_DATA%".
    # This operation is expensive, only get the binary data if the template
    # really contains the placeholder.
    if strTemplate.find('${%PROGRAM_DATA%}') != -1:
        # The template really contains the placeholder.
        tBinFile = env['GCCSYMBOLTEMPLATE_BINFILE']
        if (tBinFile == '') or (tBinFile is None):
            raise Exception(
                'The template requests the program data, but '
                'GCCSYMBOLTEMPLATE_BINFILE is not set.'
            )
        elif isinstance(tBinFile, str):
            strBinFileName = tBinFile
        else:
            strBinFileName = tBinFile.get_path()

        # Get the binary data.
        tFile = open(strBinFileName, 'rb')
        strBinData = tFile.read()
        strHexData = binascii.hexlify(strBinData)

        # Split the hex data into 64 char chunks.
        astrHexLines = []
        for iOffset in range(0, len(strHexData), 64):
            astrHexLines.append(strHexData[iOffset:iOffset+64])

        # Join the hex lines with newlines.
        strHexDump = '\n'.join(astrHexLines)

        strTemplate = strTemplate.replace(
            '${%PROGRAM_DATA%}',
            strHexDump
        )

    # Replace all symbols in the template.
    strResult = string.Template(strTemplate).safe_substitute(atSymbols)

    # Write the result.
    tFile = open(target[0].get_path(), 'wt')
    tFile.write(strResult)
    tFile.close()

    return 0


def gccsymboltemplate_emitter(target, source, env):
    # Make the target depend on the parameter.
    tTemplateFilename = env['GCCSYMBOLTEMPLATE_TEMPLATE']
    if isinstance(tTemplateFilename, str):
        SCons.Script.Depends(
            target,
            SCons.Script.File(tTemplateFilename)
        )
    else:
        SCons.Script.Depends(
            target,
            tTemplateFilename
        )
    tBinData = env['GCCSYMBOLTEMPLATE_BINFILE']
    if tBinData != '' and tBinData is not None:
        if isinstance(tBinData, str):
            SCons.Script.Depends(
                target,
                SCons.Script.File(tBinData)
            )
        else:
            SCons.Script.Depends(
                target,
                tBinData
            )

    return target, source


def gccsymboltemplate_string(target, source, env):
    return 'GccSymbolTemplate %s' % target[0].get_path()


# ----------------------------------------------------------------------------
#
# Add GccSymbolTemplate builder.
#
def ApplyToEnv(env):
    env['GCCSYMBOLTEMPLATE_TEMPLATE'] = ''
    env['GCCSYMBOLTEMPLATE_BINFILE'] = ''

    gccsymboltemplate_act = SCons.Action.Action(
        gccsymboltemplate_action,
        gccsymboltemplate_string
    )
    gccsymboltemplate_bld = SCons.Script.Builder(
        action=gccsymboltemplate_act,
        emitter=gccsymboltemplate_emitter,
        suffix='.c',
        single_source=1
    )
    env['BUILDERS']['GccSymbolTemplate'] = gccsymboltemplate_bld
