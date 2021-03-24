# -*- coding: utf-8 -*-

# ***************************************************************************
# *   Copyright (C) 2019 by Hilscher GmbH                                   *
# *   netXsupport@hilscher.com                                              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program; if not, write to the                         *
# *   Free Software Foundation, Inc.,                                       *
# *   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             *
# ***************************************************************************

import argparse
import os.path
import re

import sys

from hbi_settings import *
import hboot_image as hboot_image
import hboot_image_version as hboot_image_version

# import hboot_image
# import hboot_image_version


tParser = argparse.ArgumentParser(usage='hboot_image [options]')
tParser.add_argument(
    '--version',
    action='version',
    version=hboot_image_version.VERSION_STRING
)
tGroupe = tParser.add_mutually_exclusive_group(required=True)
tGroupe.add_argument('-n', '--netx-type',
                     dest='strNetxType',
                     choices=[
                         'NETX56',
                         'NETX90',
                         'NETX90B',
                         'NETX90C',
                         'NETX90_MPW',
                         'NETX4000_RELAXED',
                         'NETX4000',
                         'NETX4100',
                         'NETXXL_MPW'
                     ],
                     metavar='NETX',
                     help='Build the image for netx type NETX.')
tGroupe.add_argument('--netx-type-public',
                     dest='strNetxType',
                     choices=[
                         'netx90',
                         'netx90_rev0',
                         'netx90_rev1',
                         'netx90_rev2',
                         'netx90_mpw',
                         'NETX56',
                         'NETX4000_RELAXED',
                         'NETX4000',
                         'NETX4100'
                     ],
                     metavar='NETX',
                     help='Build the image for netx type public NETX.')
tParser.add_argument('-c', '--objcopy',
                     dest='strObjCopy',
                     required=False,
                     default='objcopy',
                     metavar='FILE',
                     help='Use FILE as the objcopy tool.')
tParser.add_argument('-d', '--objdump',
                     dest='strObjDump',
                     required=False,
                     default='objdump',
                     metavar='FILE',
                     help='Use FILE as the objdump tool.')
tParser.add_argument('-k', '--keyrom',
                     dest='strKeyRomPath',
                     required=False,
                     default=None,
                     metavar='FILE',
                     help='Read the keyrom data from FILE.')
tParser.add_argument('-p', '--patch-table',
                     dest='strPatchTablePath',
                     required=False,
                     default=None,
                     metavar='FILE',
                     help='Read the patch table from FILE.')
tParser.add_argument('-r', '--readelf',
                     dest='strReadElf',
                     required=False,
                     default='readelf',
                     metavar='FILE',
                     help='Use FILE as the readelf tool.')
tParser.add_argument('-v', '--verbose',
                     dest='fVerbose',
                     required=False,
                     default=False,
                     action='store_const', const=True,
                     help='Be more verbose.')
tParser.add_argument('-A', '--alias',
                     dest='astrAliases',
                     required=False,
                     action='append',
                     metavar='ALIAS=FILE',
                     help='Add an alias in the form ALIAS=FILE.')
tParser.add_argument('-D', '--define',
                     dest='astrDefines',
                     required=False,
                     action='append',
                     metavar='NAME=VALUE',
                     help='Add a define in the form NAME=VALUE.')
tParser.add_argument('-I', '--include',
                     dest='astrIncludePaths',
                     required=False,
                     action='append',
                     metavar='PATH',
                     help='Add PATH to the list of include paths.')
tParser.add_argument('-S', '--sniplib',
                     dest='astrSnipLib',
                     required=False,
                     action='append',
                     metavar='PATH',
                     help='Add PATH to the list of sniplib paths.')
tParser.add_argument('--openssl-options',
                     dest='astrOpensslOptions',
                     required=False,
                     action='append',
                     metavar='SSLOPT',
                     help='Add SSLOPT to the arguments for OpenSSL.')
tParser.add_argument('--openssl-exe',
                     dest='strOpensslExe',
                     required=False,
                     default='openssl',
                     metavar='PATH',
                     help='Add individual OpenSSL Path.')
tParser.add_argument('--openssl-rand-off',
                     dest='fOpensslRandOff',
                     required=False,
                     default=False,
                     action='store_const', const=True,
                     metavar='SSLRAND',
                     help='Set openssl randomization true or false.')
tParser.add_argument('strInputFile',
                     metavar='FILE',
                     help='Read the HBoot definition from FILE.')
tParser.add_argument('strOutputFile',
                     metavar='FILE',
                     help='Write the HBoot image to FILE.')
tArgs = tParser.parse_args()

# Set the default for the patch table here.
atDefaultPatchTables = {
    'NETX56': 'hboot_netx56_patch_table.xml',
    'NETX90': 'hboot_netx90_patch_table.xml',
    'NETX90B': 'hboot_netx90b_patch_table.xml',
    'NETX90C': 'hboot_netx90c_patch_table.xml',
    'NETX90_MPW': 'hboot_netx90_mpw_patch_table.xml',
    'NETX4000_RELAXED': 'hboot_netx4000_relaxed_patch_table.xml',
    'NETX4000': 'hboot_netx4000_patch_table.xml',
    'NETX4100': 'hboot_netx4000_patch_table.xml'
}

if tArgs.strNetxType == 'netx90':
    strNetxType = 'NETX90C'
elif tArgs.strNetxType == 'netx90_rev0':
    strNetxType = 'NETX90'
elif tArgs.strNetxType == 'netx90_rev1':
    strNetxType = 'NETX90B'
elif tArgs.strNetxType == 'netx90_rev2':
    strNetxType = 'NETX90C'
elif tArgs.strNetxType == 'netx90_mpw':
    strNetxType = 'NETX90_MPW'
else:
    strNetxType = tArgs.strNetxType


if tArgs.strPatchTablePath is None:

    path_patch_tables = os.path.join(hbi_path, "patch_tables")
    print("path_patch_tables: '%s'" % path_patch_tables)
    for file in os.listdir(path_patch_tables):
        print("-%s" % file)
    tArgs.strPatchTablePath = os.path.join(
        path_patch_tables,
        atDefaultPatchTables[strNetxType]
    )

# Parse all alias definitions.
atKnownFiles = {}
if tArgs.astrAliases is not None:
    tPattern = re.compile('([a-zA-Z0-9_]+)=(.+)$')
    for strAliasDefinition in tArgs.astrAliases:
        tMatch = re.match(tPattern, strAliasDefinition)
        if tMatch is None:
            raise Exception(
                'Invalid alias definition: "%s". '
                'It must be "ALIAS=FILE" instead.' % strAliasDefinition
            )
        strAlias = tMatch.group(1)
        strFile = tMatch.group(2)
        if strAlias in atKnownFiles:
            raise Exception(
                'Double defined alias "%s". The old value "%s" should be '
                'overwritten with "%s".' % (
                    strAlias,
                    atKnownFiles[strAlias],
                    strFile
                )
            )
        atKnownFiles[strAlias] = strFile

# Parse all defines.
atDefinitions = {}
if tArgs.astrDefines is not None:
    tPattern = re.compile('([a-zA-Z0-9_]+)=(.+)$')
    for strDefine in tArgs.astrDefines:
        tMatch = re.match(tPattern, strDefine)
        if tMatch is None:
            raise Exception('Invalid define: "%s". '
                            'It must be "NAME=VALUE" instead.' % strDefine)
        strName = tMatch.group(1)
        strValue = tMatch.group(2)
        if strName in atDefinitions:
            raise Exception(
                'Double defined name "%s". '
                'The old value "%s" should be overwritten with "%s".' % (
                    strName,
                    atKnownFiles[strName],
                    strValue
                )
            )
        atDefinitions[strName] = strValue

# Set an empty list of include paths if nothing was specified.
if tArgs.astrIncludePaths is None:
    tArgs.astrIncludePaths = []

# Set an empty list of sniplib paths if nothing was specified.
if tArgs.astrSnipLib is None:
    tArgs.astrSnipLib = []

tEnv = {'OBJCOPY': tArgs.strObjCopy,
        'OBJDUMP': tArgs.strObjDump,
        'READELF': tArgs.strReadElf,
        'HBOOT_INCLUDE': tArgs.astrIncludePaths}

tCompiler = hboot_image.HbootImage(
    tEnv,
    strNetxType,
    defines=atDefinitions,
    includes=tArgs.astrIncludePaths,
    known_files=atKnownFiles,
    patch_definition=tArgs.strPatchTablePath,
    verbose=tArgs.fVerbose,
    sniplibs=tArgs.astrSnipLib,
    keyrom=tArgs.strKeyRomPath,
    openssloptions=tArgs.astrOpensslOptions,
    opensslexe=tArgs.strOpensslExe,
    opensslrandoff=tArgs.fOpensslRandOff
)
tCompiler.parse_image(tArgs.strInputFile)
tCompiler.write(tArgs.strOutputFile)
