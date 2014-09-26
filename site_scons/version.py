# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
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
#-------------------------------------------------------------------------#


import datetime
import os
import re
import string
import subprocess
from string import Template

from SCons.Script import *


def build_version_strings(env):
	# Is the VCS ID already set?
	if not 'PROJECT_VERSION_VCS' in env:
		# The default version is 'unknown'.
		strProjectVersionVcsSystem = 'unknown'
		strProjectVersionVcsVersion = 'unknown'
		strProjectVersionVCS = 'unknown'
		strProjectVersionLastCommit = 'unknown'
		
		# Use the root folder to get the version. This is important for HG and SVN>=1.7 .
		strSconsRoot = Dir('#').abspath
		
		if os.path.exists(os.path.join(strSconsRoot, '.git')):
			if env['GIT']:
				strProjectVersionVcsSystem = 'GIT'
				# Get the GIT ID.
				try:
					strOutput = subprocess.check_output([env['GIT'], 'describe', '--abbrev=12', '--always', '--dirty=+'])
					strGitId = string.strip(strOutput)
					tMatch = re.match('[0-9a-f]{12}\+?$', strGitId)
					if not tMatch is None:
						# This is a repository with no tags. Use the raw SHA sum.
						strProjectVersionVcsVersion = strGitId
					else:
						tMatch = re.match('v(\d+\.\d+\.\d+)$', strGitId)
						if not tMatch is None:
							# This is a repository which is exactly on a tag. Use the tag name.
							strProjectVersionVcsVersion = tMatch.group(1)
						else:
							tMatch = re.match('v\d+\.\d+\.\d+-\d+-g([0-9a-f]{12}\+?)$', strGitId)
							if not tMatch is None:
								# This is a repository with commits after the last tag.
								strProjectVersionVcsVersion = tMatch.group(1)
							else:
								# The description has an unknown format.
								strProjectVersionVcsVersion = strGitId
					strProjectVersionVCS = strProjectVersionVcsSystem + strProjectVersionVcsVersion
				except:
					pass
		elif os.path.exists(os.path.join(strSconsRoot, '.hg')):
			if env['MERCURIAL']:
				strProjectVersionVcsSystem = 'HG'
				# Get the mercurial ID.
				try:
					strOutput = subprocess.check_output([env['MERCURIAL'], 'id', '-i'])
					strHgId = string.strip(strOutput)
					strProjectVersionVcsVersion = strHgId
					strProjectVersionVCS = strProjectVersionVcsSystem + strProjectVersionVcsVersion
				except:
					pass
				
				# Is this version completely checked in?
				if strHgId[-1]=='+':
					strProjectVersionLastCommit = 'SNAPSHOT'
				else:
					# Get the date of the last commit.
					try:
						strOutput = subprocess.check_output([env['MERCURIAL'], 'log', '-r', strHgId, '--template', '{date|hgdate}'])
						strHgDate = string.strip(strOutput)
						tMatch = re.match('(\d+)\s+([+-]?\d+)', strHgDate)
						if not tMatch is None:
							tTimeStamp = datetime.datetime.fromtimestamp(float(tMatch.group(1)))
							strProjectVersionLastCommit = '%04d%02d%02d_%02d%02d%02d' % (tTimeStamp.year, tTimeStamp.month, tTimeStamp.day, tTimeStamp.hour, tTimeStamp.minute, tTimeStamp.second)
					except:
						pass
		elif os.path.exists(os.path.join(strSconsRoot, '.svn')):
			if env['SVNVERSION']:
				strProjectVersionVcsSystem = 'SVN'
				
				# Get the SVN version.
				try:
					strSvnId = subprocess.check_output([env['SVNVERSION']])
					strProjectVersionVcsVersion = strSvnId
					strProjectVersionVCS = strProjectVersionVcsSystem + strProjectVersionVcsVersion
				except:
					pass
		
		# Add the version to the environment.
		env['PROJECT_VERSION_VCS'] = strProjectVersionVCS
		env['PROJECT_VERSION_LAST_COMMIT'] = strProjectVersionLastCommit
		env['PROJECT_VERSION_VCS_SYSTEM'] = strProjectVersionVcsSystem
		env['PROJECT_VERSION_VCS_VERSION'] = strProjectVersionVcsVersion



def get_project_version_vcs(env):
	build_version_strings(env)
	return env['PROJECT_VERSION_VCS']



def get_project_version_last_commit(env):
	build_version_strings(env)
	return env['PROJECT_VERSION_LAST_COMMIT']



def get_project_version_vcs_system(env):
	build_version_strings(env)
	return env['PROJECT_VERSION_VCS_SYSTEM']



def get_project_version_vcs_version(env):
	build_version_strings(env)
	return env['PROJECT_VERSION_VCS_VERSION']



def version_action(target, source, env):
	global PROJECT_VERSION
	
	# Split up the project version.
	version_info = PROJECT_VERSION.split('.')
	
	# Apply the project version to the environment.
	aSubst = dict({
		'PROJECT_VERSION_MAJOR':version_info[0],
		'PROJECT_VERSION_MINOR':version_info[1],
		'PROJECT_VERSION_MICRO':version_info[2],
		'PROJECT_VERSION_VCS':env['PROJECT_VERSION_VCS'],
		'PROJECT_VERSION': PROJECT_VERSION,
		'PROJECT_VERSION_VCS_SYSTEM':env['PROJECT_VERSION_VCS_SYSTEM'],
		'PROJECT_VERSION_VCS_VERSION':env['PROJECT_VERSION_VCS_VERSION'],
	})
	
	# Read the template.
	tTemplate = Template(source[0].get_contents())
	
	# Read the destination (if exists).
	try:
		dst_oldtxt = target[0].get_contents()
	except IOError:
		dst_oldtxt = ''
	
	# Filter the src file.
	dst_newtxt = tTemplate.safe_substitute(aSubst)
	if dst_newtxt!=dst_oldtxt:
		# Overwrite the file.
		dst_file = open(target[0].get_path(), 'w')
		dst_file.write(dst_newtxt)
		dst_file.close()



def version_emitter(target, source, env):
	global PROJECT_VERSION
	
	
	build_version_strings(env)
	
	# Make the target depend on the project version and the VCS ID.
	Depends(target, SCons.Node.Python.Value(PROJECT_VERSION))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_VCS']))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_LAST_COMMIT']))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_VCS_SYSTEM']))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_VCS_VERSION']))
	
	return target, source


def version_string(target, source, env):
	return 'Version %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add version builder.
	#
	env['GIT'] = env.Detect('git') or 'git'
	env['MERCURIAL'] = env.Detect('hg') or env.Detect('thg') or 'hg'
	env['SVNVERSION'] = env.Detect('svnversion') or 'svnversion'
	
	version_act = SCons.Action.Action(version_action, version_string)
	version_bld = Builder(action=version_act, emitter=version_emitter, single_source=1)
	env['BUILDERS']['Version'] = version_bld

	env.AddMethod(get_project_version_vcs, "Version_GetVcsId")
	env.AddMethod(get_project_version_last_commit, "Version_GetLastCommit")
	env.AddMethod(get_project_version_vcs_system, "Version_GetVcsSystem")
	env.AddMethod(get_project_version_vcs_version, "Version_GetVcsVersion")

