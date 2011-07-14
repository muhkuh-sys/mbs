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
	atSourceData = array.array('L')
	atSourceData.fromstring(strSourceData)

	# Loop over all elements.
	for ulElement in atSourceData:
		file_target.write(' %08x\n'%ulElement)

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

