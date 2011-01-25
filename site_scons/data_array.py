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

from SCons.Script import *


def dataarray_action(target, source, env):
	file_target = open(target[0].get_path(), 'w')
	
	aucSourceData = source[0].get_contents()
	sizSourceData = len(aucSourceData)
	
	strArrayName = env['DATAARRAY_NAME']
	sizBytesPerLine = env['DATAARRAY_BYTES_PER_LINE']
	
	file_target.write("const unsigned char %s[%d] =\n"%(strArrayName,sizSourceData))
	file_target.write("{\n");
	for iCnt in xrange(0, sizSourceData, sizBytesPerLine):
		aucChunk = aucSourceData[iCnt:iCnt+sizBytesPerLine]
		file_target.write("\t");
		file_target.write(', '.join(['0x%02X'%ord(ucByte) for ucByte in aucChunk]))
		if( iCnt+sizBytesPerLine<sizSourceData ):
			file_target.write(',')
		file_target.write("\n")
	file_target.write("};\n");
	file_target.close()
	
	
	# Write the header file.
	strDefineName = string.replace(string.upper(os.path.basename(target[1].get_path())), '.', '_')
	file_target = open(target[1].get_path(), 'w')
	file_target.write("#ifndef __%s__\n" % strDefineName)
	file_target.write("#define __%s__\n" % strDefineName)
	file_target.write("\n")
	file_target.write("#ifdef __cplusplus\n")
	file_target.write("extern \"C\" {\n")
	file_target.write("#endif\n")
	file_target.write("\n")
	file_target.write("extern const unsigned char %s[%d];\n"%(strArrayName,sizSourceData))
	file_target.write("\n")
	file_target.write("#ifdef __cplusplus\n")
	file_target.write("}\n")
	file_target.write("#endif\n")
	file_target.write("\n")
	file_target.write("#endif  /* __%s__ */\n" % strDefineName)
	file_target.write("\n")
	file_target.close()
	
	return 0


def dataarray_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, SCons.Node.Python.Value(env['DATAARRAY_NAME']))
	Depends(target, SCons.Node.Python.Value(env['DATAARRAY_BYTES_PER_LINE']))
	
	# Add the header file to the list of targets.
	strBase,strOldExt = os.path.splitext(target[0].get_path())
	strHeader = strBase + '.h'
	target.append(strHeader)
	
	return target, source


def dataarray_string(target, source, env):
	return 'DataArray %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add dataarray builder.
	#
	env['DATAARRAY_NAME'] = 'aucData'
	env['DATAARRAY_BYTES_PER_LINE'] = 16

	dataarray_act = SCons.Action.Action(dataarray_action, dataarray_string)
	dataarray_bld = Builder(action=dataarray_act, emitter=dataarray_emitter, suffix='.c', single_source=1)
	env['BUILDERS']['DataArray'] = dataarray_bld

