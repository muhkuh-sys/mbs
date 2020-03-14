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


import argparse
import datetime
import os
import re
import string
import subprocess

if __name__ != '__main__':
    import SCons.Script


def build_version_strings(strProjectRootPath, strGit, strMercurial,
                          strSvnversion):
    # The default version is 'unknown'.
    strProjectVersionVcsSystem = 'unknown'
    strProjectVersionVcsVersion = 'unknown'
    strProjectVersionVcsVersionLong = 'unknown'
    strProjectVersionVCS = 'unknown'
    strProjectVersionVCSLong = 'unknown'
    strProjectVersionLastCommit = 'unknown'
    strProjectVersionVCSURL = 'unknown'

    if os.path.exists(os.path.join(strProjectRootPath, '.git')):
        if strGit is not None:
            strProjectVersionVcsSystem = 'GIT'
            # Get the GIT ID.
            try:
                strCmd = ('%s describe --abbrev=12 --always '
                          '--dirty=+ --long' % strGit)
                tProcess = subprocess.Popen(
                    strCmd,
                    stdout=subprocess.PIPE,
                    cwd=strProjectRootPath,
                    shell=True
                )
                strOutput, strError = tProcess.communicate()
                if tProcess.returncode != 0:
                    raise Exception('git failed!')
                strGitId = string.strip(strOutput)
                tMatch = re.match(r'[0-9a-f]{12}\+?$', strGitId)
                if tMatch is not None:
                    # This is a repository with no tags.
                    # Use the raw SHA sum.
                    strProjectVersionVcsVersion = strGitId
                    strProjectVersionVcsVersionLong = strGitId
                else:
                    tMatch = re.match(
                        r'v(\d+(\.\d+)*)-(\d+)-g([0-9a-f]{12})$',
                        strGitId
                    )
                    if tMatch is not None:
                        ulRevsSinceTag = int(tMatch.group(3))
                        if ulRevsSinceTag == 0:
                            # This is a repository which is exactly on a
                            # tag. Use the tag name.
                            strProjectVersionVcsVersion = tMatch.group(1)
                            strProjectVersionVcsVersionLong = '%s-%s' % (
                                tMatch.group(1),
                                tMatch.group(4)
                            )
                        else:
                            # This is a repository with commits after
                            # the last tag. Use the checkin ID.
                            strProjectVersionVcsVersion = tMatch.group(4)
                            strProjectVersionVcsVersionLong = tMatch.group(4)
                    else:
                        tMatch = re.match(
                            r'v(\d+(\.\d+)*)-(\d+)-g([0-9a-f]{12})\+?$',
                            strGitId
                        )
                        if tMatch is not None:
                            ulRevsSinceTag = int(tMatch.group(3))
                            if ulRevsSinceTag == 0:
                                # This is a repository on a tag, but it has
                                # modified files. Use the tag name and the '+'.
                                strProjectVersionVcsVersion = '%s+' % (
                                    tMatch.group(1)
                                )
                                strProjectVersionVcsVersionLong = '%s-%s+' % (
                                    tMatch.group(1),
                                    tMatch.group(4)
                                )
                            else:
                                # This is a repository with commits after
                                # the last tag and modified files.
                                # Use the checkin ID and the '+'.
                                strProjectVersionVcsVersion = '%s+' % (
                                    tMatch.group(4)
                                )
                                strProjectVersionVcsVersionLong = '%s+' % (
                                    tMatch.group(4)
                                )
                        else:
                            # The description has an unknown format.
                            strProjectVersionVcsVersion = strGitId
                            strProjectVersionVcsVersionLong = strGitId

                strProjectVersionVCS = (
                    strProjectVersionVcsSystem +
                    strProjectVersionVcsVersion
                )
                strProjectVersionVCSLong = (
                    strProjectVersionVcsSystem +
                    strProjectVersionVcsVersionLong
                )

                strCmd = '%s config --get remote.origin.url' % strGit
                tProcess = subprocess.Popen(
                    strCmd,
                    stdout=subprocess.PIPE,
                    cwd=strProjectRootPath,
                    shell=True
                )
                strOutput, strError = tProcess.communicate()
                if tProcess.returncode != 0:
                    raise Exception('git failed!')
                strProjectVersionVCSURL = string.strip(strOutput)
            except subprocess.CalledProcessError:
                pass

    elif os.path.exists(os.path.join(strProjectRootPath, '.hg')):
        if strMercurial is not None:
            strProjectVersionVcsSystem = 'HG'
            # Get the mercurial ID.
            try:
                strCmd = '%s id -i' % strMercurial
                tProcess = subprocess.Popen(
                    strCmd,
                    stdout=subprocess.PIPE,
                    cwd=strProjectRootPath,
                    shell=True
                )
                strOutput, strError = tProcess.communicate()
                if tProcess.returncode != 0:
                    raise Exception('hg failed!')
                strHgId = string.strip(strOutput)
                strProjectVersionVcsVersion = strHgId
                strProjectVersionVCS = (
                    strProjectVersionVcsSystem + strProjectVersionVcsVersion
                )
            except subprocess.CalledProcessError:
                pass

            # Is this version completely checked in?
            if strHgId[-1] == '+':
                strProjectVersionLastCommit = 'SNAPSHOT'
            else:
                # Get the date of the last commit.
                try:
                    strCmd = '%s log -r %s --template {date|hgdate}' % (
                        strMercurial,
                        strHgId
                    )
                    strOutput = subprocess.Popen(
                        strCmd,
                        stdout=subprocess.PIPE,
                        cwd=strProjectRootPath,
                        shell=True
                    )
                    strOutput, strError = tProcess.communicate()
                    if tProcess.returncode != 0:
                        raise Exception('hg failed!')
                    strHgDate = string.strip(strOutput)
                    tMatch = re.match(r'(\d+)\s+([+-]?\d+)', strHgDate)
                    if tMatch is not None:
                        tTimeStamp = datetime.datetime.fromtimestamp(
                            float(tMatch.group(1))
                        )
                        strProjectVersionLastCommit = (
                            '%04d%02d%02d_%02d%02d%02d' % (
                                tTimeStamp.year,
                                tTimeStamp.month,
                                tTimeStamp.day,
                                tTimeStamp.hour,
                                tTimeStamp.minute,
                                tTimeStamp.second
                            )
                        )
                except subprocess.CalledProcessError:
                    pass
    elif os.path.exists(os.path.join(strProjectRootPath, '.svn')):
        if strSvnversion is not None:
            strProjectVersionVcsSystem = 'SVN'

            # Get the SVN version.
            try:
                strCmd = '%s' % strSvnversion
                strSvnId = subprocess.Popen(
                    strCmd,
                    stdout=subprocess.PIPE,
                    cwd=strProjectRootPath,
                    shell=True
                )
                strOutput, strError = tProcess.communicate()
                if tProcess.returncode != 0:
                    raise Exception('svnversion failed!')
                strProjectVersionVcsVersion = strSvnId
                strProjectVersionVCS = (
                    strProjectVersionVcsSystem + strProjectVersionVcsVersion
                )
            except subprocess.CalledProcessError:
                pass

    tVersion = {
        'VcsSystem': strProjectVersionVcsSystem,
        'VcsVersion': strProjectVersionVcsVersion,
        'VcsVersionLong': strProjectVersionVcsVersionLong,
        'VCS': strProjectVersionVCS,
        'VCSLong': strProjectVersionVCSLong,
        'LastCommit': strProjectVersionLastCommit,
        'VCSURL': strProjectVersionVCSURL
    }

    return tVersion


def add_version_strings_to_env(env):
    # Is the VCS ID already set?
    if 'PROJECT_VERSION_VCS' not in env:
        # Use the root folder to get the version. This is important for HG
        # and SVN>=1.7, but also for GIT as the build folder can be a
        # different filesystem.
        strSconsRoot = SCons.Script.Dir('#').abspath
        tVersion = build_version_strings(
            strSconsRoot,
            env['GIT'],
            env['MERCURIAL'],
            env['SVNVERSION']
        )

        # Add the version to the environment.
        env['PROJECT_VERSION_VCS'] = tVersion['VCS']
        env['PROJECT_VERSION_VCS_LONG'] = tVersion['VCSLong']
        env['PROJECT_VERSION_LAST_COMMIT'] = tVersion['LastCommit']
        env['PROJECT_VERSION_VCS_SYSTEM'] = tVersion['VcsSystem']
        env['PROJECT_VERSION_VCS_VERSION'] = tVersion['VcsVersion']
        env['PROJECT_VERSION_VCS_VERSION_LONG'] = tVersion['VcsVersionLong']
        env['PROJECT_VERSION_VCS_URL'] = tVersion['VCSURL']


def get_project_version_vcs(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS']


def get_project_version_vcs_long(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS_LONG']


def get_project_version_last_commit(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_LAST_COMMIT']


def get_project_version_vcs_system(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS_SYSTEM']


def get_project_version_vcs_version(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS_VERSION']


def get_project_version_vcs_version_long(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS_VERSION_LONG']


def get_project_version_vcs_url(env):
    add_version_strings_to_env(env)
    return env['PROJECT_VERSION_VCS_URL']


def version_action(target, source, env):
    # Split up the project version.
    version_info = SCons.Script.PROJECT_VERSION.split('.')

    # Apply the project version to the environment.
    aSubst = dict({
        'PROJECT_VERSION_MAJOR': version_info[0],
        'PROJECT_VERSION_MINOR': version_info[1],
        'PROJECT_VERSION_MICRO': version_info[2],
        'PROJECT_VERSION_VCS': env['PROJECT_VERSION_VCS'],
        'PROJECT_VERSION_VCS_LONG': env['PROJECT_VERSION_VCS_LONG'],
        'PROJECT_VERSION': SCons.Script.PROJECT_VERSION,
        'PROJECT_VERSION_VCS_SYSTEM': env['PROJECT_VERSION_VCS_SYSTEM'],
        'PROJECT_VERSION_VCS_VERSION': env['PROJECT_VERSION_VCS_VERSION'],
    })

    # Read the template.
    tTemplate = string.Template(source[0].get_contents())

    # Read the destination (if exists).
    try:
        dst_oldtxt = target[0].get_contents()
    except IOError:
        dst_oldtxt = ''

    # Filter the src file.
    dst_newtxt = tTemplate.safe_substitute(aSubst)
    if dst_newtxt != dst_oldtxt:
        # Overwrite the file.
        dst_file = open(target[0].get_path(), 'w')
        dst_file.write(dst_newtxt)
        dst_file.close()


def version_emitter(target, source, env):
    add_version_strings_to_env(env)

    # Make the target depend on the project version and the VCS ID.
    env.Depends(target, SCons.Node.Python.Value(SCons.Script.PROJECT_VERSION))
    env.Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_VCS']))
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_VCS_LONG'])
    )
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_LAST_COMMIT'])
    )
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_VCS_SYSTEM'])
    )
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_VCS_VERSION'])
    )
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_VCS_VERSION_LONG'])
    )
    env.Depends(target, SCons.Node.Python.Value(
        env['PROJECT_VERSION_VCS_URL'])
    )

    return target, source


def version_string(target, source, env):
    return 'Version %s' % target[0].get_path()


def ApplyToEnv(env):
    # ---------------------------------------------------------------------------
    #
    # Add version builder.
    #
    env['GIT'] = env.Detect('git') or 'git'
    env['MERCURIAL'] = env.Detect('hg') or env.Detect('thg') or 'hg'
    env['SVNVERSION'] = env.Detect('svnversion') or 'svnversion'

    version_act = SCons.Action.Action(version_action, version_string)
    version_bld = SCons.Script.Builder(
        action=version_act,
        emitter=version_emitter,
        single_source=1
    )
    env['BUILDERS']['Version'] = version_bld

    env.AddMethod(get_project_version_vcs,
                  "Version_GetVcsId")
    env.AddMethod(get_project_version_vcs_long,
                  "Version_GetVcsIdLong")
    env.AddMethod(get_project_version_last_commit,
                  "Version_GetLastCommit")
    env.AddMethod(get_project_version_vcs_system,
                  "Version_GetVcsSystem")
    env.AddMethod(get_project_version_vcs_version,
                  "Version_GetVcsVersion")
    env.AddMethod(get_project_version_vcs_version_long,
                  "Version_GetVcsVersionLong")
    env.AddMethod(get_project_version_vcs_url,
                  'Version_GetVcsUrl')


if __name__ == '__main__':
    tParser = argparse.ArgumentParser(
        description='Get the project version from the VCS.'
    )
    tParser.add_argument(
        'strProjectRootPath',
        help='The path to the project root.'
    )
    tParser.add_argument(
        '--git',
        dest='strGit',
        default=None,
        help='The path to the "git" tool.'
    )
    tParser.add_argument(
        '--hg',
        dest='strMercurial',
        default=None,
        help='The path to the "hg" tool.'
    )
    tParser.add_argument(
        '--svnversion',
        dest='strSvnversion',
        default=None,
        help='The path to the "svnversion" tool.'
    )
    tArgs = tParser.parse_args()

    tVersion = build_version_strings(
        tArgs.strProjectRootPath,
        tArgs.strGit,
        tArgs.strMercurial,
        tArgs.strSvnversion
    )
    print('%s,%s,%s' % (
        tVersion['VCS'],
        tVersion['VCSLong'],
        tVersion['VCSURL']
    ))
