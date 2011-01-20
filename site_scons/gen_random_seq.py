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

from SCons.Script import *


def prn_action(target, source, env):
	prn_size = env['PRN_SIZE']
	prn_seed = env['PRN_SEED']
	prn_inc = env['PRN_INC']
	
	aBinData = array.array('L', [0]*prn_size)
	
	# Write the start and add value.
	aBinData[0] = prn_seed
	aBinData[1] = prn_inc
	
	prn_reg = prn_seed
	for ulAdr in range(2, prn_size):
		prn_reg += prn_inc
		prn_reg &= 0xffffffff
		aBinData[ulAdr] = prn_reg
	
	# Write the complete array to a file.
	file_out = open(target[0].get_path(), 'wb')
	try:
		aBinData.tofile(file_out)
	finally:
		file_out.close()
	
	return None


def prn_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, SCons.Node.Python.Value(env['PRN_SIZE']))
	Depends(target, SCons.Node.Python.Value(env['PRN_SEED']))
	Depends(target, SCons.Node.Python.Value(env['PRN_INC']))
	
	return target, source


def prn_string(target, source, env):
	return 'Prn %s' % target[0].get_path()


def ApplyToEnv(env):                                                                                                                                                                                            
	#----------------------------------------------------------------------------                                                                                                                           
	#                                                                                                                                                                                                       
	# Add secmem builder.                                                                                                                                                                                 
	#                                                                                                                                                                                                       
	env['PRN_SIZE'] = 0x00080000
	env['PRN_SEED'] = 269230517
	env['PRN_INC']  = 275155577
	
	prn_act = SCons.Action.Action(prn_action, prn_string)
	prn_bld = Builder(action=prn_act, emitter=prn_emitter, suffix='.bin')
	env['BUILDERS']['Prn'] = prn_bld
