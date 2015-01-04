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
	
	# Get the macros from the ELF file.
	atElfMacros = elf_support.get_macro_definitions(env, source[0].get_path())
	atSymbols.update(atElfMacros)
	
	# Get the debug information from the ELF file.
	atElfDebugSymbols = elf_support.get_debug_symbols(env, source[0].get_path())
	atSymbols.update(atElfDebugSymbols)

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
