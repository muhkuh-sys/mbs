# -*- coding: utf-8 -*-

import argparse
import re

import hboot_image


tParser = argparse.ArgumentParser(usage='usage: hboot_image [options]')
tParser.add_argument('-n', '--netx-type',
                     dest='strNetxType',
                     required=True,
                     choices=['NETX56', 'NETX90_MPW', 'NETX90_MPW', 'NETX4000_RELAXED'],
                     metavar='NETX',
                     help='Build the image for netx type NETX.')
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
tParser.add_argument('-I', '--include',
                     dest='astrIncludePaths',
                     required=False,
                     action='append',
                     metavar='PATH',
                     help='Add PATH to the list of include paths.')
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
    'NETX90_MPW': 'hboot_netx90_mpw_patch_table.xml',
    'NETX90_MPW_APP': 'hboot_netx90_mpw_app_patch_table.xml',
    'NETX4000_RELAXED': 'hboot_netx4000_relaxed_patch_table.xml'
}
if tArgs.strPatchTablePath is None:
    tArgs.strPatchTablePath = atDefaultPatchTables[tArgs.strNetxType]

# Parse all alias definitions.
atKnownFiles = {}
if tArgs.astrAliases is not None:
    tPattern = re.compile('([a-zA-Z0-9_]+)=(.+)$')
    for strAliasDefinition in tArgs.astrAliases:
        tMatch = re.match(tPattern, strAliasDefinition)
        if tMatch is None:
            raise Exception('Invalid alias definition: "%s". It must be "ALIAS=FILE" instead.' % strAliasDefinition)
        strAlias = tMatch.group(1)
        strFile = tMatch.group(2)
        if strAlias in atKnownFiles:
            raise Exception('Double defined alias "%s". The old value "%s" should be overwritten with "%s".' % (strAlias, atKnownFiles[strAlias], strFile))
        atKnownFiles[strAlias] = strFile

# Set an empty list of include paths if nothing was specified.
if tArgs.astrIncludePaths is None:
    tArgs.astrIncludePaths = []

tEnv = {'OBJCOPY': tArgs.strObjCopy,
        'OBJDUMP': tArgs.strObjDump,
        'READELF': tArgs.strReadElf,
        'HBOOT_INCLUDE': tArgs.astrIncludePaths}

tCompiler = hboot_image.HbootImage(tEnv, tArgs.strNetxType, patch_definition=tArgs.strPatchTablePath, known_files=atKnownFiles, verbose=tArgs.fVerbose)
tCompiler.parse_image(tArgs.strInputFile)
tCompiler.write(tArgs.strOutputFile)
