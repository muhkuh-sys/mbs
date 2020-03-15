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


import SCons

import elf_support

import array
import os.path
import subprocess
import re
import xml.etree.ElementTree


aBootBlockElements = dict({
    'MagCok':             0,

    'MemCtrl':            1,
    'Speed':              1,
    'Res0':               1,

    'AppEnt':             2,
    'AppChksm':           3,
    'AppFilSiz':          4,
    'AppSrtAdd':          5,
    'Signt':              6,

    'SdramGeneralCtrl':   7,
    'ExpBusReg':          7,
    'SramCtrl':           7,

    'SdramTimingCtrl':    8,
    'IoRegMode0':         8,

    'IoRegMode1':         9,
    'Res1':               9,

    'IfConf1':            10,
    'Res2':               10,

    'IfConf2':            11,
    'Res3':               11,

    'MiscAsicCtrl':       12,
    'Serial':             13,
    'SrcType':            14,
    'BootChksm':          15
})


def string_to_number(strNumber):
    # Try the C syntax (hex digits with '0x' or '0X' prefix).
    match_obj = re.match("[ \t]*0[xX]([0-9a-fA-F]+)", strNumber)
    if match_obj:
        # Convert C hex string to number.
        number = int(match_obj.group(1), 16)
    else:
        # Try the normal decimal syntax.
        try:
            number = int(strNumber)
        except ValueError:
            number = None
    return number


def find_device_node(tNetxXml, strDeviceTyp, strChipTyp, strDevice):
    # Find all nodes of the requested type.
    tPlatformElement = None
    for tElement in tNetxXml.findall(strDeviceTyp):
        if tElement.get('netx_version') == strChipTyp:
            tPlatformElement = tElement
            break

    if tPlatformElement is None:
        raise Exception('Chiptyp %s not found in %s list.' % (
            strChipTyp,
            strDeviceTyp
        ))

    tDeviceElement = None
    for tElement in tPlatformElement.findall('Device'):
        if ('id' in tElement.attrib) and (tElement.attrib['id'] == strDevice):
            tDeviceElement = tElement
            break

    if tDeviceElement is None:
        raise Exception('Device %s not found in %s %s list.' % (
            strDevice,
            strChipTyp,
            strDeviceTyp
        ))

    return tDeviceElement


def apply_parameters(tDeviceElement, aBootblock):
    for tElement in tDeviceElement.findall('Param'):
        if 'name' not in tElement.attrib:
            raise Exception('Error in netx xml: the Param node has no '
                            'name attribute!')
        strFieldName = tElement.attrib['name']
        if strFieldName not in aBootBlockElements:
            raise Exception('Error in netx xml: the Param node has an '
                            'unknown value for the name attribute: %s' %
                            strFieldName)

        ulValue = string_to_number(tElement.text.strip())
        aBootblock[aBootBlockElements[strFieldName]] = ulValue


def bootblock_action(target, source, env):
    # Get the source filename.
    strSourceFileName = source[0].get_path()

    # Get the chiptyp info.
    strAsicTyp = env['ASIC_TYP']
    if strAsicTyp == 'NETX500':
        strChipTyp = 'netx 500'
    elif strAsicTyp == 'NETX56':
        strChipTyp = 'netx 56'
    elif strAsicTyp == 'NETX50':
        strChipTyp = 'netx 50'
    elif strAsicTyp == 'NETX10':
        strChipTyp = 'netx 10'
    elif strAsicTyp == 'NETX4000_RELAXED' or strAsicTyp == 'NETX90_MPW':
        raise Exception(
            'The ASIC typ "%s" does not support ABOOT images.' % strAsicTyp
        )
    else:
        raise Exception('Invalid ASIC typ: "%s"' % strAsicTyp)

    # If this is an ELF file it should end with ".elf".
    strDummy, strExt = os.path.splitext(strSourceFileName)
    if strExt == '.elf':
        # This seems to be an ELF file.

        # Generate a temp filename for the binary.
        strBinFileName = strSourceFileName + '.bin'

        # Extract the segments.
        atSegments = elf_support.get_segment_table(env, strSourceFileName)
        # Get the estimated binary size from the segments.
        ulEstimatedBinSize = elf_support.get_estimated_bin_size(atSegments)
        # Do not create files larger than 512MB.
        if ulEstimatedBinSize >= 0x20000000:
            raise Exception('The resulting file seems to extend 512MBytes. '
                            'Too scared to continue!')

        # Extract the binaries.
        subprocess.check_call([
            env['OBJCOPY'],
            '-O', 'binary',
            strSourceFileName,
            strBinFileName
        ])

        ulExecAddress = elf_support.get_exec_address(env, strSourceFileName)
        ulLoadAddress = elf_support.get_load_address(atSegments)

        # Get the application data.
        tBinFile = open(strBinFileName, 'rb')
        strBinFile = tBinFile.read()
        tBinFile.close()

        # Pad the application size to a multiple of dwords.
        uiPadBytes = len(strBinFile) & 3
        if uiPadBytes != 0:
            uiPadBytes = 4 - uiPadBytes
            strBinFile += '\0' * uiPadBytes
        # Get the size of the evetually padded data.
        ulApplicationDwordSize = len(strBinFile) / 4
        aulApplicationData = array.array('I')
        aulApplicationData.fromstring(strBinFile)

        # Build the application checksum.
        ulApplicationChecksum = 0
        for ulData in aulApplicationData:
            ulApplicationChecksum += ulData
            ulApplicationChecksum &= 0xffffffff

        aBootBlock = array.array('I', [0]*16)
        aBootBlock[0x00] = 0xf8beaf00              # Magic cookie.
        aBootBlock[0x01] = 0x00000000              # unCtrl
        aBootBlock[0x02] = ulExecAddress           # execution address
        aBootBlock[0x03] = ulApplicationChecksum   # application checksum
        aBootBlock[0x04] = ulApplicationDwordSize  # application dword size
        aBootBlock[0x05] = ulLoadAddress           # load address
        aBootBlock[0x06] = 0x5854454e              # 'NETX' signature
        aBootBlock[0x07] = 0x00000000              # krams
        aBootBlock[0x08] = 0x00000000              # krams
        aBootBlock[0x09] = 0x00000000              # krams
        aBootBlock[0x0a] = 0x00000000              # krams
        aBootBlock[0x0b] = 0x00000000              # krams
        aBootBlock[0x0c] = 0x00000001              # misc_asic_ctrl dummy
        aBootBlock[0x0d] = 0x00000000              # user data
        aBootBlock[0x0e] = 0x00000000              # src type
    else:
        # Try to interpret the file as a bootable image.
        # For now just check for the magic cookie at the start.

        tBinFile = open(strSourceFileName, 'rb')
        strHeader = tBinFile.read(64)
        strApp = tBinFile.read()
        tBinFile.close()

        aBootBlock = array.array('I', strHeader)
        aulApplicationData = array.array('I', strApp)

        if aBootBlock[0x00] == 0xf8beaf00:
            # This seems to be a boot image.

            # Build the application checksum.
            ulApplicationChecksum = 0
            for ulData in aulApplicationData:
                ulApplicationChecksum += ulData
                ulApplicationChecksum &= 0xffffffff

            # Get the application size in 32bit chunks.
            ulApplicationDwordSize = len(aulApplicationData)

            # Override the application checksum and size in the header.
            aBootBlock[0x03] = ulApplicationChecksum
            aBootBlock[0x04] = ulApplicationDwordSize
        else:
            # This is an unknown image.
            raise Exception('The input file could not be identified as an '
                            'ELF file or a boot image!')

    # Test if we need to read the xml file.
    if(
        isinstance(env['BOOTBLOCK_SRC'], str) or
        isinstance(env['BOOTBLOCK_DST'], str)
    ):
        # Read the xml file.
        tNetxXml = xml.etree.ElementTree.ElementTree()
        tNetxXml.parse(env['BOOTBLOCK_XML'])

    # Apply source options.
    if isinstance(env['BOOTBLOCK_SRC'], dict):
        for offset, value in env['BOOTBLOCK_SRC'].items():
            uiOffset = int(offset)
            ulValue = int(value)
            if uiOffset < 0 or uiOffset > 16:
                raise Exception('invalid offset in BOOTBLOCK_SRC '
                                'parameters: %s' % uiOffset)
            aBootBlock[uiOffset] = ulValue
    elif isinstance(env['BOOTBLOCK_SRC'], str):
        # Find the source device.
        tDeviceElement = find_device_node(
            tNetxXml,
            'src',
            strChipTyp,
            env['BOOTBLOCK_SRC']
        )
        apply_parameters(tDeviceElement, aBootBlock)
    else:
        raise Exception(
            'The parameter BOOTBLOCK_SRC has an invalid type (%s), only dict '
            'and str can be processed.' % repr(type(env['BOOTBLOCK_SRC']))
        )

    # Apply destination options.
    if isinstance(env['BOOTBLOCK_DST'], dict):
        for offset, value in env['BOOTBLOCK_DST'].items():
            uiOffset = int(offset)
            ulValue = int(value)
            if uiOffset < 0 or uiOffset > 16:
                raise Exception('invalid offset in BOOTBLOCK_DST '
                                'parameters: %s' % uiOffset)
            aBootBlock[uiOffset] = ulValue
    elif isinstance(env['BOOTBLOCK_DST'], str):
        tDeviceElement = find_device_node(
            tNetxXml,
            'dst',
            strChipTyp,
            env['BOOTBLOCK_DST']
        )
        apply_parameters(tDeviceElement, aBootBlock)
    else:
        raise Exception(
            'The parameter BOOTBLOCK_DST has an invalid type (%s), only dict '
            'and str can be processed.' % repr(type(env['BOOTBLOCK_DST']))
        )

    # Build the bootblock checksum.
    ulBootblockChecksum = 0
    for uiCnt in range(0, 15):
        ulBootblockChecksum += aBootBlock[uiCnt]
        ulBootblockChecksum &= 0xffffffff
    ulBootblockChecksum = (ulBootblockChecksum - 1) ^ 0xffffffff
    aBootBlock[0x0f] = ulBootblockChecksum

    # Write the bootimage.
    fOutput = open(target[0].get_path(), 'wb')
    aBootBlock.tofile(fOutput)
    aulApplicationData.tofile(fOutput)
    fOutput.close()

    return None


def bootblock_emitter(target, source, env):
    # Make the target depend on the xml file and the parameter.
    env.Depends(target, env['BOOTBLOCK_XML'])
    env.Depends(target, SCons.Node.Python.Value(env['ASIC_TYP']))
    env.Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_SRC']))
    env.Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_DST']))
    env.Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_USERDATA']))

    return target, source


def bootblock_string(target, source, env):
    return 'BootBlock %s' % target[0].get_path()


def ApplyToEnv(env):
    # Sanity checks.
    if array.array('I').itemsize != 4:
        raise Exception(
            'The item size of an array of type "I" is not 32bit. This is an '
            'internal error or the bootblock builder.'
        )

    # ------------------------------------------------------------------------
    #
    # Add bootblock builder.
    #
    env['BOOTBLOCK_XML'] = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'netx.xml'
    )
    env['BOOTBLOCK_SRC'] = ''
    env['BOOTBLOCK_DST'] = ''
    env['BOOTBLOCK_USERDATA'] = 0

    bootblock_act = SCons.Action.Action(bootblock_action, bootblock_string)
    bootblock_bld = SCons.Script.Builder(
        action=bootblock_act,
        emitter=bootblock_emitter,
        suffix='.bin',
        single_source=1,
        src_suffix='.elf',
        src_builder='Elf'
    )
    env['BUILDERS']['BootBlock'] = bootblock_bld
