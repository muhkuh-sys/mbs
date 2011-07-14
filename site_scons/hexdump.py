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


import array
import os
import string

from SCons.Script import *


def hexdump_action(target, source, env):
	file_target = open(target[0].get_path(), 'w')

	# Read the source data into an array.
	strSourceData = source[0].get_contents()

	iElemSize = env['HEXDUMP_ELEMENT_SIZE']
	if iElemSize==1:
		strArrayFormat = 'B'
	elif iElemSize==2:
		strArrayFormat = 'H'
	elif iElemSize==4:
		strArrayFormat = 'L'
	else:
		raise Exception('Invalid element size, must be 1, 2 or 3, but it is %d' % iElemSize)

	atSourceData = array.array(strArrayFormat)
	atSourceData.fromstring(strSourceData)

	strPrintFormat = ' %%0%dx\n' % iElemSize

	# Loop over all elements.
	for tElement in atSourceData:
		file_target.write(strPrintFormat%tElement)

	# Close the output file.
	file_target.close()
	
	return 0


def hexdump_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, SCons.Node.Python.Value(env['HEXDUMP_ELEMENT_SIZE']))
	
	return target, source


def hexdump_string(target, source, env):
	return 'HexDump %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add hexdump builder.
	#
	env['HEXDUMP_ELEMENT_SIZE'] = 4

	hexdump_act = SCons.Action.Action(hexdump_action, hexdump_string)
	hexdump_bld = Builder(action=hexdump_act, emitter=hexdump_emitter, suffix='.hex', single_source=1)
	env['BUILDERS']['HexDump'] = hexdump_bld

