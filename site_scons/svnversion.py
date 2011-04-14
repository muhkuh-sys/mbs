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
from string import Template

from SCons.Script import *


def svnversion_action(target, source, env):
	global PROJECT_VERSION
	
	# Split up the project version.
	version_info = PROJECT_VERSION.split('.')
	
	# Apply the project version to the environment.
	aSubst = dict({
		'PROJECT_VERSION_MAJ':version_info[0],
		'PROJECT_VERSION_MIN':version_info[1],
		'PROJECT_VERSION_SVN':env['PROJECT_VERSION_SVN'],
		'PROJECT_VERSION': '%s.%s.%s'%(version_info[0], version_info[1], env['PROJECT_VERSION_SVN']),
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


def svnversion_emitter(target, source, env):
	global PROJECT_VERSION
	
	
	# Is the SVN version already set?
	if not 'PROJECT_VERSION_SVN' in env:
		# No -> get the SVN version.
		
		# The default for the SVN version is 'unknown'.
		project_version_svn = 'unknown'
		
		if env['SVNVERSION']:
			# get the svn version
			child = os.popen(env['SVNVERSION']+' -n')
			project_version_svn = child.read()
			err = child.close()
			if err:
				project_version_svn = 'unknown'
		
		# Add the SVN version to the environment.
		env['PROJECT_VERSION_SVN'] = project_version_svn
	
	# Make the target depend on the project version and the SVN version.
	Depends(target, SCons.Node.Python.Value(PROJECT_VERSION))
	Depends(target, SCons.Node.Python.Value(env['PROJECT_VERSION_SVN']))
	
	return target, source


def svnversion_string(target, source, env):
	return 'SVNVersion %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add svnversion builder.
	#
	env['SVNVERSION'] = env.Detect('svnversion') or 'svnversion'
	
	svnversion_act = SCons.Action.Action(svnversion_action, svnversion_string)
	svnversion_bld = Builder(action=svnversion_act, emitter=svnversion_emitter, single_source=1)
	env['BUILDERS']['SVNVersion'] = svnversion_bld

