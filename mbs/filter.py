# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2012 by Christoph Thelen                                #
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

import os.path
import string
import sys


def create_substitute_dict(aCfg, strMbsDir):
	# Get the scons path.
	strSconsPath = aCfg['scons_path']
	
	# Get the project version.
	strProjectVersion = '%d.%d' % (aCfg['project_version_maj'], aCfg['project_version_min'])
	
	# Get the tools.
	aToolPaths = []
	for aTool in aCfg['tools']:
		strToolPath = os.path.join(aCfg['depack_path'], aTool['group'], aTool['name']).replace('\\', '/')
		aToolPaths.append('\'%s-%s\': \'%s\'' % (aTool['name'],aTool['version'], strToolPath))
	
	strTools  = 'dict({' + ','.join(aToolPaths) + '})'
	
	# apply the project version to the environment
	aSubstitute = dict({
		'NOTE': 'NOTE: This file was generated by setup.py . Any changes will be lost!',
		'PYTHON': sys.executable,
		'SCONS_DIR': strSconsPath,
		'PROJECT_VERSION': strProjectVersion,
		'TOOLS': strTools,
		'MBS_DIR' : strMbsDir
	})
	return aSubstitute


def filter_file(aSubstitute, strDstPath, strSrcPath):
	print 'Filter %s -> %s' % (strSrcPath, strDstPath)
	
	# Read the template.
	src_file = open(strSrcPath, 'r')
	src_txt = src_file.read()
	src_file.close()
	tTemplate = string.Template(src_txt)
	dst_newtxt = tTemplate.safe_substitute(aSubstitute)
	
	# Read the destination (if exists).
	try:
		dst_file = open(strDstPath, 'r')
		dst_oldtxt = dst_file.read()
		dst_file.close()
	except IOError:
		dst_oldtxt = ''
	
	if dst_newtxt!=dst_oldtxt:
		# overwrite the file
		dst_file = open(strDstPath, 'w')
		dst_file.write(dst_newtxt)
		dst_file.close()
		# Copy the permission bits.
		shutil.copymode(strSrcPath, strDstPath)



def apply(aCfg):
	# Get the relative path from the current folder to the Muhkuh build system.
	strMbsDir = os.path.relpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..'))

	aSubstitute = create_substitute_dict(aCfg, strMbsDir)
	for strDst,strSrc in aCfg['filter'].items():
		# Get the source file from the project folder.
		strPrjSrc = os.path.join(strMbsDir, strSrc)
		# Create the destination folder.
		strDstFolder = os.path.dirname(strDst)
		if strDstFolder!='' and os.path.exists(strDstFolder)==False:
			os.makedirs(strDstFolder)
		filter_file(aSubstitute, strDst, strPrjSrc)


