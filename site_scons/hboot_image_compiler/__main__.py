# -*- coding: utf-8 -*-

import argparse
import re

import hboot_image


tParser = argparse.ArgumentParser(usage='usage: hboot_image [options]')
tParser.add_argument('-n', '--netx-type',
                     dest='uiNetxType',
                     type=int,
                     required=True,
                     choices=[56, 4000],
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
    56: 'hboot_netx56_patch_table.xml',
    4000: 'hboot_netx4000_patch_table.xml'
}
if tArgs.strPatchTablePath is None:
    tArgs.strPatchTablePath = atDefaultPatchTables[tArgs.uiNetxType]

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

# Show all parameters.
if tArgs.fVerbose:
    print 'netX type:   %d' % tArgs.uiNetxType
    print ''
    print 'Input file:  %s' % tArgs.strInputFile
    print 'Output file: %s' % tArgs.strOutputFile
    print ''
    print 'Patch table: %s' % tArgs.strPatchTablePath
    print ''
    print 'OBJCOPY: %s' % tArgs.strObjCopy
    print 'OBJDUMP: %s' % tArgs.strObjDump
    print 'READELF: %s' % tArgs.strReadElf

    if len(tArgs.astrIncludePaths) == 0:
        print 'No include paths.'
    else:
        print 'Include paths:'
        for strPath in tArgs.astrIncludePaths:
            print '\t%s' % strPath

    if len(atKnownFiles) == 0:
        print 'No alias definitions.'
    else:
        print 'Alias definitions:'
        for strAlias, strFile in atKnownFiles.iteritems():
            print '\t%s = %s' % (strAlias, strFile)

tCompiler = hboot_image.HbootImage(tEnv, tArgs.uiNetxType, patch_definition=tArgs.strPatchTablePath, known_files=atKnownFiles)
tCompiler.parse_image(tArgs.strInputFile)
tCompiler.write(tArgs.strOutputFile)
