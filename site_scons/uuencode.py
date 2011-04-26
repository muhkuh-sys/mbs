# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2011 by Christoph Thelen                                #
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

import uu
from string import Template                                                                                                                                                                                                                                                                                                
from types import ListType

import SCons
import SCons.Node.FS
from SCons.Script import *

import elf_support


def uuencode_action(target, source, env):
	if env['UUE_ELF']=='':
		strUUEPre = env['UUE_PRE']
		strUUEPost = env['UUE_POST']
	else:
		tElfFile = env['UUE_ELF']
		if isinstance(tElfFile, ListType) or isinstance(tElfFile, SCons.Node.NodeList):
			strElfFileName = tElfFile[0].get_path()
		elif isinstance(tElfFile, SCons.Node.FS.Base):
			strElfFileName = tElfFile.get_path()
		else:
			strElfFileName = tElfFile
		
		# Extract the segments.
		atSegments = elf_support.get_segment_table(env, strElfFileName)
		
		# Get the load address.
		ulLoadAddress = elf_support.get_load_address(atSegments)
		# Get the estimated binary size from the segments.
		ulEstimatedBinSize = elf_support.get_estimated_bin_size(atSegments)
		# Get the execution address.
		ulExecAddress = elf_support.get_exec_address(env, strElfFileName)
		
		aSubst = dict({
			'EXEC_DEZ': ulExecAddress,
			'EXEC_HEX': '%x'%ulExecAddress,
			'LOAD_DEZ': ulLoadAddress,
			'LOAD_HEX': '%x'%ulLoadAddress,
			'SIZE_DEZ': ulEstimatedBinSize,
			'SIZE_HEX': '%x'%ulEstimatedBinSize
		})
		
		strUUEPre = Template(env['UUE_PRE']).safe_substitute(aSubst)
		strUUEPost = Template(env['UUE_POST']).safe_substitute(aSubst)
	
	file_source = open(source[0].get_path(), 'rb')
	file_target = open(target[0].get_path(), 'wt')
	
	file_target.write(strUUEPre)
	uu.encode(file_source, file_target)
	file_target.write(strUUEPost)
	
	file_source.close()
	file_target.close()
	return 0


def uuencode_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, SCons.Node.Python.Value(env['UUE_PRE']))
	Depends(target, SCons.Node.Python.Value(env['UUE_POST']))
	Depends(target, env['UUE_ELF'])
	
	return target, source


def uuencode_string(target, source, env):
	return 'UUEncode %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add uuencode builder.
	#
	env['UUE_PRE'] = ''
	env['UUE_POST'] = ''
	env['UUE_ELF'] = ''
	
	uuencode_act = SCons.Action.Action(uuencode_action, uuencode_string)
	uuencode_bld = Builder(action=uuencode_act, emitter=uuencode_emitter, suffix='.uue', single_source=1, src_suffix='.bin')
	env['BUILDERS']['UUEncode'] = uuencode_bld

