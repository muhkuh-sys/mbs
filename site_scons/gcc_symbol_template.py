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


import elf_support
import os
import re
import string

from string import Template

from SCons.Script import *


def gccsymboltemplate_action(target, source, env):
	# Get the symbol table from the elf.
	atSymbols = elf_support.get_symbol_table(env, source[0].get_path())
	
	# Get the debug information from the ELF file.
	tXmlDebugInfo = elf_support.get_debug_info(env, source[0].get_path())
	tRoot = tXmlDebugInfo.getroot()

	# Find all enumeration values.
	for tNode in tRoot.findall('.//enumeration_type'):
		for tEnumNode in tNode.findall('enumerator'):
			ulValue = int(tEnumNode.get('const_value'))
			strName = tEnumNode.get('name')
			if strName is None:
				raise Exception('Missing name!')
			atSymbols[strName] = ulValue

	# Find all macro definitions.
	for tNode in tRoot.findall('MergedMacros/Macro'):
		strName = tNode.get('name')
		strValue = tNode.get('value')
		atSymbols[strName] = strValue
	
	# Find all structure members and their offset.
	reLocation = re.compile('\d+ byte block: \d+ ([0-9a-f]+)')
	for tNode in tRoot.findall('.//structure_type'):
		strStructureName = tNode.get('name')
		if not strStructureName is None:
			for tStructNode in tNode.findall('member'):
				strLoc = tStructNode.get('data_member_location')
				strName = tStructNode.get('name')
				if (not strLoc is None) and (not strName is None):
					tObj = reLocation.match(strLoc)
					if not tObj is None:
						strMemberName = 'OFFSETOF:' + strStructureName + ':' + strName
						ulOffset = int(tObj.group(1), 16)
						atSymbols[strMemberName] = ulOffset

	# Read the template.
	tTemplateFilename = env['GCCSYMBOLTEMPLATE_TEMPLATE']
	if isinstance(tTemplateFilename, basestring):
		strTemplateFilename = tTemplateFilename
	else:
		# Assume this is a file.
		strTemplateFilename = tTemplateFilename.get_path()
	tFile = open(strTemplateFilename, 'rt')
	strTemplateFile = tFile.read()
	tFile.close()
	
	# Replace all symbols in the template.
	strResult = string.Template(strTemplateFile).safe_substitute(atSymbols)
	
	# Write the result.
	tFile = open(target[0].get_path(), 'wt')
	tFile.write(strResult)
	tFile.close()
	
	return 0


def gccsymboltemplate_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, File(env['GCCSYMBOLTEMPLATE_TEMPLATE']))
	
	return target, source


def gccsymboltemplate_string(target, source, env):
	return 'GccSymbolTemplate %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add GccSymbolTemplate builder.
	#
	env['GCCSYMBOLTEMPLATE_TEMPLATE'] = ''
	
	gccsymboltemplate_act = SCons.Action.Action(gccsymboltemplate_action, gccsymboltemplate_string)
	gccsymboltemplate_bld = Builder(action=gccsymboltemplate_act, emitter=gccsymboltemplate_emitter, suffix='.c', single_source=1)
	env['BUILDERS']['GccSymbolTemplate'] = gccsymboltemplate_bld
