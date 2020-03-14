# -*- coding: utf-8 -*-


import hboot_image_compiler.hboot_image

from types import ListType
import os.path

import SCons.Script


def __get_clean_known_files(atKnownFiles):
    atClean = {}

    # Iterate over all known files.
    for strKey, tFile in atKnownFiles.items():
        # The file must be either a string, a SCons.Node.FS.File object or a
        # SCons.Node.NodeList object.
        if isinstance(tFile, str):
            strFile = tFile
        elif isinstance(tFile, SCons.Node.FS.File):
            strFile = tFile.get_path()
        elif isinstance(tFile, SCons.Node.NodeList):
            # The list must have exactly one entry.
            if len(tFile) != 1:
                raise Exception(
                    'Key "%s" has more than one file in the known files.' %
                    strKey
                )
            strFile = tFile[0].get_path()
        else:
            raise Exception(
                'Unknown type for key "%s" in the known files.' %
                strKey
            )

        atClean[strKey] = strFile

    return atClean


def __hboot_get_patch_table(env):
    strPatchDefinition = None
    if(
        'HBOOTIMAGE_PATCH_DEFINITION' in env and
        env['HBOOTIMAGE_PATCH_DEFINITION'] is not None
    ):
        tPatchDefinition = env['HBOOTIMAGE_PATCH_DEFINITION']
        if(
            isinstance(tPatchDefinition, ListType) or
            isinstance(tPatchDefinition, SCons.Node.NodeList) is True
        ):
            if len(tPatchDefinition) != 1:
                raise Exception('Too many sources for the patch definition.')

            tPatchDefinition = tPatchDefinition[0]

        if isinstance(tPatchDefinition, SCons.Node.FS.File):
            strPatchDefinition = tPatchDefinition.get_path()

        else:
            strPatchDefinition = tPatchDefinition

    else:
        # Get the chip type.
        strRelPatchDefinition = None
        strAsicTyp = env['ASIC_TYP']
        if strAsicTyp == 'NETX4000_RELAXED':
            strRelPatchDefinition = 'hboot_netx4000_relaxed_patch_table.xml'
        elif strAsicTyp == 'NETX4000':
            strRelPatchDefinition = 'hboot_netx4000_patch_table.xml'
        elif strAsicTyp == 'NETX4100':
            strRelPatchDefinition = 'hboot_netx4000_patch_table.xml'
        elif strAsicTyp == 'NETX90_MPW':
            strRelPatchDefinition = 'hboot_netx90_mpw_patch_table.xml'
        elif strAsicTyp == 'NETX90':
            strRelPatchDefinition = 'hboot_netx90_patch_table.xml'
        elif strAsicTyp == 'NETX90_MPW_APP':
            strRelPatchDefinition = 'hboot_netx90_mpw_app_patch_table.xml'
        elif strAsicTyp == 'NETX90_APP':
            strRelPatchDefinition = 'hboot_netx90_app_patch_table.xml'
        elif strAsicTyp == 'NETX56':
            strRelPatchDefinition = 'hboot_netx56_patch_table.xml'
        elif strAsicTyp == 'NETXXL_MPW':
            strRelPatchDefinition = 'hboot_netxxl_mpw_patch_table.xml'
        else:
            raise Exception('Invalid ASIC typ: "%s"' % strAsicTyp)

        strPatchDefinition = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            strRelPatchDefinition
        )

    return strPatchDefinition


def __hboot_definition_scan(node, env, path):
    # This is the list of dependencies.
    atDependencies = []

    fNoDependencyScan = False
    if 'HBOOTIMAGE_NO_DEPENDENCY_SCAN' in env:
        fNoDependencyScan = bool(env['HBOOTIMAGE_NO_DEPENDENCY_SCAN'])

    if fNoDependencyScan is not True:
        if node.exists() is True:
            atKnownFiles = {}
            if 'HBOOTIMAGE_KNOWN_FILES' in env:
                atK = env['HBOOTIMAGE_KNOWN_FILES']
                if atK is not None:
                    atKnownFiles = __get_clean_known_files(atK)

            astrIncludePaths = None
            if 'HBOOTIMAGE_INCLUDE_PATHS' in env:
                atValues = env['HBOOTIMAGE_INCLUDE_PATHS']
                if (atValues is not None) and (len(atValues) != 0):
                    astrIncludePaths = []
                    astrIncludePaths.extend(atValues)

            astrSnippetSearchPaths = None
            if len(env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS']) != 0:
                astrSnippetSearchPaths = []
                astrSnippetSearchPaths.extend(
                    env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS']
                )

            atDefines = {}
            if 'HBOOTIMAGE_DEFINES' in env:
                atValues = env['HBOOTIMAGE_DEFINES']
                if atValues is not None:
                    atDefines = dict(atValues)

            fVerbose = False
            if 'HBOOTIMAGE_VERBOSE' in env:
                fVerbose = bool(env['HBOOTIMAGE_VERBOSE'])

            strAsicTyp = env['ASIC_TYP']
            strSrcFile = node.get_path()
            tCompiler = hboot_image_compiler.hboot_image.HbootImage(
                env,
                strAsicTyp,
                includes=astrIncludePaths,
                sniplibs=astrSnippetSearchPaths,
                known_files=atKnownFiles,
                defines=atDefines,
                verbose=fVerbose
            )
            astrDependencies = tCompiler.dependency_scan(strSrcFile)
            # Translate the list of paths to a list of
            # SCons.Node.FS.File objects.
            atDependencies = []
            for strFile in astrDependencies:
                atDependencies.append(SCons.Script.File(strFile))

    return atDependencies


def __hboot_image_action(target, source, env):
    atKnownFiles = {}
    if 'HBOOTIMAGE_KNOWN_FILES' in env:
        atK = env['HBOOTIMAGE_KNOWN_FILES']
        if atK is not None:
            atKnownFiles = __get_clean_known_files(atK)

    strKeyRom = None
    if 'HBOOTIMAGE_KEYROM_XML' in env:
        strKeyRom = env['HBOOTIMAGE_KEYROM_XML']

    astrIncludePaths = None
    if 'HBOOTIMAGE_INCLUDE_PATHS' in env:
        atValues = env['HBOOTIMAGE_INCLUDE_PATHS']
        if (atValues is not None) and (len(atValues) != 0):
            astrIncludePaths = []
            astrIncludePaths.extend(atValues)

    astrSnippetSearchPaths = None
    if len(env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS']) != 0:
        astrSnippetSearchPaths = []
        astrSnippetSearchPaths.extend(env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS'])

    atDefines = {}
    if 'HBOOTIMAGE_DEFINES' in env:
        atValues = env['HBOOTIMAGE_DEFINES']
        if atValues is not None:
            atDefines = dict(atValues)

    fVerbose = False
    if 'HBOOTIMAGE_VERBOSE' in env:
        fVerbose = bool(env['HBOOTIMAGE_VERBOSE'])

    strPatchDefinition = __hboot_get_patch_table(env)

    strAsicTyp = env['ASIC_TYP']
    tCompiler = hboot_image_compiler.hboot_image.HbootImage(
        env,
        strAsicTyp,
        patch_definition=strPatchDefinition,
        includes=astrIncludePaths,
        sniplibs=astrSnippetSearchPaths,
        known_files=atKnownFiles,
        defines=atDefines,
        keyrom=strKeyRom,
        verbose=fVerbose
    )
    tCompiler.parse_image(source[0].get_path())
    tCompiler.write(target[0].get_path())

    return 0


def __hboot_image_emitter(target, source, env):
    if 'HBOOTIMAGE_KNOWN_FILES' in env:
        atKnownFiles = env['HBOOTIMAGE_KNOWN_FILES']
        if atKnownFiles is not None:
            atKnownFiles = __get_clean_known_files(atKnownFiles)
            for strId, strPath in atKnownFiles.items():
                # NOTE: Only add the reference here as a string.
                # The source scanner will check if this reference is really
                # used.
                env.Depends(
                    target,
                    SCons.Node.Python.Value(
                        'KNOWN_FILE:%s:%s' %
                        (strId, strPath))
                )

    if 'HBOOTIMAGE_KEYROM_XML' in env:
        tKeyrom = env['HBOOTIMAGE_KEYROM_XML']
        if tKeyrom is not None:
            env.Depends(target, tKeyrom)

    if 'HBOOTIMAGE_INCLUDE_PATHS' in env:
        astrIncludePaths = env['HBOOTIMAGE_INCLUDE_PATHS']
        if astrIncludePaths is not None and len(astrIncludePaths) != 0:
            env.Depends(
                target,
                SCons.Node.Python.Value(
                    'INCLUDE_PATH:' + ':'.join(astrIncludePaths)
                )
            )

    if 'HBOOTIMAGE_SNIPLIB_SEARCHPATHS' in env:
        astrSnipLibs = env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS']
        if astrSnipLibs is not None and len(astrSnipLibs) != 0:
            env.Depends(
                target,
                SCons.Node.Python.Value(
                    'SNIPLIB_SEARCHPATH:' + ':'.join(astrSnipLibs)
                )
            )

    if 'HBOOTIMAGE_DEFINES' in env:
        atDefines = env['HBOOTIMAGE_DEFINES']
        if atDefines is not None:
            for strKey, tValue in atDefines.items():
                env.Depends(
                    target,
                    SCons.Node.Python.Value(
                        'DEFINE:%s:%s' %
                        (strKey, str(tValue))
                    )
                )

    strPatchDefinition = __hboot_get_patch_table(env)
    env.Depends(target, strPatchDefinition)

    fVerbose = False
    if 'HBOOTIMAGE_VERBOSE' in env:
        fVerbose = bool(env['HBOOTIMAGE_VERBOSE'])
    env.Depends(target, SCons.Node.Python.Value(str(fVerbose)))

    fNoDependencyScan = False
    if 'HBOOTIMAGE_NO_DEPENDENCY_SCAN' in env:
        fNoDependencyScan = bool(env['HBOOTIMAGE_NO_DEPENDENCY_SCAN'])
    env.Depends(target, SCons.Node.Python.Value(str(fNoDependencyScan)))

    return target, source


def __hboot_image_string(target, source, env):
    return 'HBootImage %s' % target[0].get_path()


# ---------------------------------------------------------------------------
#
# Add HBootImageNew builder.
#
def ApplyToEnv(env):
    env['HBOOTIMAGE_PATCH_DEFINITION'] = None
    env['HBOOTIMAGE_KNOWN_FILES'] = None
    env['HBOOTIMAGE_KEYROM_XML'] = None
    env['HBOOTIMAGE_INCLUDE_PATHS'] = None
    env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS'] = [
        'sniplib',
        'src/sniplib',
        'targets/snippets'
    ]
    env['HBOOTIMAGE_DEFINES'] = None
    env['HBOOTIMAGE_VERBOSE'] = False
    env['HBOOTIMAGE_NO_DEPENDENCY_SCAN'] = False

    hboot_image_act = SCons.Action.Action(
        __hboot_image_action,
        __hboot_image_string
    )
    hboot_image_scanner = SCons.Scanner.Scanner(
        function=__hboot_definition_scan
    )
    hboot_image_bld = SCons.Script.Builder(
        action=hboot_image_act,
        emitter=__hboot_image_emitter,
        suffix='.xml',
        single_source=1,
        source_scanner=hboot_image_scanner)
    env['BUILDERS']['HBootImage'] = hboot_image_bld
