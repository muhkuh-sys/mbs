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


import os
import string
from string import Template

from SCons.Script import *


def version_action(target, source, env):
	global PROJECT_VERSION
	
	# Split up the project version.
	version_info = PROJECT_VERSION.split('.')
	
	# Apply the project version to the environment.
	aSubst = dict({
		'PROJECT_VERSION_MAJ':version_info[0],
		'PROJECT_VERSION_MIN':version_info[1],
		'PROJECT_VERSION_SUB':env['PROJECT_VERSION_SUB'],
		'PROJECT_VERSION': '%s.%s.%s'%(version_info[0], version_info[1], env['PROJECT_VERSION_SUB']),
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
	
	
	# Is the SVN version already set?
	if not 'PROJECT_VERSION_SUB' in env:
		# The default version is 'unknown'.
		project_version_sub = 'unknown'
		
		if os.path.exists('.hg'):
			if env['MERCURIAL']:
				# Get the mercurial ID.
				child = os.popen(env['MERCURIAL']+' id -i')
				project_version_sub = child.read()
				err = child.close()
				if err:
					project_version_sub = 'unknown'
		elif os.path.exists('.svn'):
			if env['SVNVERSION']:
				# get the svn version
				child = os.popen(env['SVNVERSION'])
				project_version_sub = child.read()
				err = child.close()
				if err:
					project_version_sub = 'unknown'
		
		# Add the version to the environment.
		env['PROJECT_VERSION_SUB'] = string.strip(project_version_sub)
	
	# Make the target depend on the project version and the SUB version.
	Depends(target, SCons.Node.Python.Value(PROJECT_VERSION))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_SUB']))
	
	return target, source


def version_string(target, source, env):
	return 'Version %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add version builder.
	#
	env['MERCURIAL'] = env.Detect('hg') or env.Detect('thg') or 'hg'
	env['SVNVERSION'] = env.Detect('svnversion') or 'svnversion'
	
	version_act = SCons.Action.Action(version_action, version_string)
	version_bld = Builder(action=version_act, emitter=version_emitter, single_source=1)
	env['BUILDERS']['Version'] = version_bld

