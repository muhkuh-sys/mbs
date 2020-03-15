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


import atexit
import imp
import os
import re
import subprocess
import SCons


# Import all local modules.
import archive
import artifact
import artifact_version
import bootblock
import build_properties
import data_array
import diff
import filter
import flex_zip
import gcc_symbol_template
import gen_random_seq
import hash
import hboot_image
import hboot_snippet
import hexdump
import iflash_image
import objimport
import pom_template
import svnversion
import uuencode
import version
#import xsl_transform


# ---------------------------------------------------------------------------
#
# Accept 'clean' target like make as an alternative to '-c'. This makes it
# much easier to work with an IDE like KDevelop.
#
if 'clean' in SCons.Script.COMMAND_LINE_TARGETS:
    SCons.Script.Alias(
        'clean',
        SCons.Node.FS.get_default_fs().SConstruct_dir.abspath
    )
    SCons.Script.Main.SetOption('clean', 1)


# ---------------------------------------------------------------------------
#
# Display the complete command line if any command failed.
#
# TODO: GetBuildFailures only reports scons errors. If an exception occured,
#       this list is empty and the function reports a successful build right
#       after the stack dump. How can I detect this here?
#
def display_build_status():
    from SCons.Script import GetBuildFailures
    bf_all = GetBuildFailures()
    if bf_all:
        # iterate over all failures and print the command
        for bf in bf_all:
            if bf and bf.node and bf.command:
                print('Failed command for %s:\n' % str(bf.node))
                print(' '.join(bf.command))
        print("!!!!!!!!!!!!!!!")
        print("!!! FAILED !!!!")
        print("!!!!!!!!!!!!!!!")


atexit.register(display_build_status)


def find_first_tool(strToolPattern):
    strToolName = None

    tPattern = re.compile(strToolPattern)
    for strKey in SCons.Script.TOOLS:
        tMatch = re.search(tPattern, strKey)
        if tMatch is not None:
            strToolName = strKey
            break

    return strToolName


def get_tool(env, strToolName):
    tMod = None
    try:
        strPath = SCons.Script.TOOLS[strToolName]
        strModulName = strToolName.replace('-', '_').replace('.', '_')
        fp, pathname, description = imp.find_module(strModulName, [strPath])
        try:
            tMod = imp.load_module(strModulName, fp, pathname, description)
        finally:
            # Since we may exit via an exception, close fp explicitly.
            if fp:
                fp.close()
    except KeyError:
        pass

    if tMod is None:
        raise Exception(
            strToolName,
            'The requested tool is not part of the configuration. '
            'Add it to setup.xml and rerun mbs.')

    return tMod


def CreateEnvironment(env, astrToolPatterns=None):
    # Create the new environment.
    tEnvNew = SCons.Environment.Environment()
    tEnvNew.Decider('MD5')

    if astrToolPatterns is not None:
        for strToolPattern in astrToolPatterns:
            strId = find_first_tool(strToolPattern)
            if strId is None:
                raise Exception(
                    'Nothing found searching for a tool matching the '
                    'pattern "%s".' % strToolPattern
                )
            add_tool_to_environment(tEnvNew, strId)

    archive.ApplyToEnv(tEnvNew)
    artifact.ApplyToEnv(tEnvNew)
    artifact_version.ApplyToEnv(tEnvNew)
    bootblock.ApplyToEnv(tEnvNew)
    build_properties.ApplyToEnv(tEnvNew)
    data_array.ApplyToEnv(tEnvNew)
    diff.ApplyToEnv(tEnvNew)
    filter.ApplyToEnv(tEnvNew)
    flex_zip.ApplyToEnv(tEnvNew)
    gcc_symbol_template.ApplyToEnv(tEnvNew)
    gen_random_seq.ApplyToEnv(tEnvNew)
    hash.ApplyToEnv(tEnvNew)
    hboot_image.ApplyToEnv(tEnvNew)
    hboot_snippet.ApplyToEnv(tEnvNew)
    hexdump.ApplyToEnv(tEnvNew)
    iflash_image.ApplyToEnv(tEnvNew)
    objimport.ApplyToEnv(tEnvNew)
    pom_template.ApplyToEnv(tEnvNew)
    ApplyToEnv(tEnvNew)
    svnversion.ApplyToEnv(tEnvNew)
    uuencode.ApplyToEnv(tEnvNew)
    version.ApplyToEnv(tEnvNew)
#    xsl_transform.ApplyToEnv(tEnvNew)

    # Add the reference to the list of environments.
    if env is not None:
        tEnvNew.Replace(MBS_ENVIRONMENT_LIST=env['MBS_ENVIRONMENT_LIST'])

    return tEnvNew


def add_tool_to_environment(env, strToolIdAndVersion):
    tTool = get_tool(env, strToolIdAndVersion)
    tTool.ApplyToEnv(env)


def set_build_path(env, build_path, source_path, sources):
    # Convert the sources to a list.
    if isinstance(sources, str):
        sources = SCons.Script.Split(sources)

    # Build the files in a separate directory.
    env.VariantDir(build_path, source_path, duplicate=0)

    # Replace the source path at the beginning of each entry in sources.
    astrSourcesInBuiltdir = []
    for strPath in sources:
        # Does the path start with the source path?
        if strPath[:len(source_path)] == source_path:
            # Yes -> replace it with the build path.
            strBuildPath = build_path + strPath[len(source_path):]
        else:
            # No -> do not replace anything.
            strBuildPath = strPath
        astrSourcesInBuiltdir.append(strBuildPath)

    return astrSourcesInBuiltdir


def create_compiler_environment(
    env,
    strAsicTyp,
    aAttributesCommon,
    linker_attributes=None,
    name=None
):
    # Find the library paths for gcc and newlib.

    # Use the common attributes both for the detect and the linker phase if no
    # special linker attributes were specified.
    if linker_attributes is None:
        linker_attributes = aAttributesCommon

    # Use the ASIC typ as the default name.
    if name is None:
        name = strAsicTyp

    # Prepend an 'm' to each attribute and create a set from this list.
    aMAttributesCommon = set(['m'+strAttr for strAttr in aAttributesCommon])

    # Prepend an '-m' to each attribute.
    aOptAttributesCommon = ['-m'+strAttr for strAttr in aAttributesCommon]
    aOptAttributesLinker = ['-m'+strAttr for strAttr in linker_attributes]

    # Get the mapping for multiple library search directories.
    strMultilibPath = None
    aCmd = [env['CC']]
    aCmd.extend(aOptAttributesCommon)
    aCmd.append('-print-multi-lib')
    proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
    strOutput = proc.communicate()[0].decode("utf-8", "replace")
    for match_obj in re.finditer(
        '^([^;]+);@?([^\r\n\t ]+)',
        strOutput,
        re.MULTILINE
    ):
        strPath = match_obj.group(1)
        aAttr = set(match_obj.group(2).split('@'))
        if aAttr == aMAttributesCommon:
            strMultilibPath = strPath
            break

    if strMultilibPath is None:
        raise Exception(
            'Could not find multilib configuration for attributes %s' %
            (','.join(aAttributesCommon))
        )

    strGccLibPath = os.path.join(
        env['GCC_LIBRARY_DIR_COMPILER'],
        strMultilibPath
    )
    strNewlibPath = os.path.join(
        env['GCC_LIBRARY_DIR_ARCHITECTURE'],
        strMultilibPath
    )

    env_new = env.Clone()
    env_new.Append(CCFLAGS=aOptAttributesLinker)
    env_new.Replace(LIBPATH=[strGccLibPath, strNewlibPath])
    env_new.Append(CPPDEFINES=[['ASIC_TYP', 'ASIC_TYP_%s' % strAsicTyp]])
    env_new.Replace(ASIC_TYP='%s' % strAsicTyp)

    # Add the new environment to the list.
    setattr(env['MBS_ENVIRONMENT_LIST'], name, env_new)

    return env_new


def ApplyToEnv(env):
    env.AddMethod(set_build_path, 'SetBuildPath')
    env.AddMethod(create_compiler_environment, 'CreateCompilerEnv')
    env.AddMethod(get_tool, 'GetTool')
    env.AddMethod(CreateEnvironment, "CreateEnvironment")
