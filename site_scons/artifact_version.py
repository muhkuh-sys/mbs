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


def build_artifact_version_strings(env):
	# Is the VCS ID already set?
	if not 'ARTIFACT_VERSION' in env:
		# The default version is 'unknown'.
		strArtifactVersion = 'unknown'
		
		# Use the root folder to get the version.
		strSconsRoot = Dir('#').abspath
		
		if os.path.exists(os.path.join(strSconsRoot, '.git')):
			if env['GIT']:
				# Get the GIT ID.
				try:
					strOutput = subprocess.check_output([env['GIT'], 'describe', '--abbrev=12', '--always', '--dirty=+'])
					strGitId = string.strip(strOutput)
					tMatch = re.match('v(\d+\.\d+\.\d+)$', strGitId)
					if not tMatch is None:
						# This is a repository which is exactly on a tag. Use the tag name.
						strArtifactVersion = tMatch.group(1)
					else:
						strArtifactVersion = 'SNAPSHOT'
				except:
					pass
		
		# Add the version to the environment.
		env['ARTIFACT_VERSION'] = strArtifactVersion



def get_artifact_version(env):
	build_artifact_version_strings(env)
	return env['ARTIFACT_VERSION']



def artifact_version_action(target, source, env):
	# Apply the artifact version to the environment.
	aSubst = dict({
		'ARTIFACT_VERSION': env['ARTIFACT_VERSION']
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



def artifact_version_emitter(target, source, env):
	build_artifact_version_strings(env)
	
	# Make the target depend on the artifact version.
	Depends(target, SCons.Node.Python.Value(env['ARTIFACT_VERSION']))
	
	return target, source


def artifact_version_string(target, source, env):
	return 'ArtifactVersion %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add artifact version builder.
	#
	env['GIT'] = env.Detect('git') or 'git'
	
	artifact_version_act = SCons.Action.Action(artifact_version_action, artifact_version_string)
	artifact_version_bld = Builder(action=artifact_version_act, emitter=artifact_version_emitter, single_source=1)
	env['BUILDERS']['ArtifactVersion'] = artifact_version_bld

	env.AddMethod(get_artifact_version, "ArtifactVersion_Get")

