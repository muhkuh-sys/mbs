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


from SCons.Script import *

import elf_support


def bootblock_action(target, source, env):
	# Get the source filename.
	strElfFileName = source[0].get_path()
	
	# Generate a temp filename for the binary.
	strBinFileName = strElfFileName + '.bin'
	
	# Extract the segments.
	atSegments = elf_support.get_segment_table(env, strElfFileName)
	# Get the estimated binary size from the segments.
	ulEstimatedBinSize = elf_support.get_estimated_bin_size(atSegments)
	# Do not create files larger than 512MB.
	if ulEstimatedBinSize>=0x20000000:
		raise Exception("The resulting file seems to extend 512MBytes. Too scared to continue!")
	
	# Extract the binaries.
	subprocess.check_call([env['OBJCOPY'], '-O', 'binary', strElfFileName, strBinFileName])
	
	ulExecAddress = elf_support.get_exec_address(env, strElfFileName)
	ulLoadAddress = elf_support.get_load_address(atSegments)
	
	# Get the application data.
	ulApplicationSize = os.stat(strBinFileName).st_size
	if (ulApplicationSize&3)!=0:
		raise Exception("The application size is no multiple of dwords!")
	fApplicationFile = open(strBinFileName, 'rb')
	aulApplicationData = array.array('L')
	aulApplicationData.fromfile(fApplicationFile, ulApplicationSize/4)
	
	# Build the application checksum.
	ulApplicationChecksum = 0
	for ulData in aulApplicationData:
		ulApplicationChecksum += ulData
		ulApplicationChecksum &= 0xffffffff
	
	aBootBlock = array.array('L', [0]*16)
	aBootBlock[0x00] = 0xf8beaf00			# Magic cookie.
	aBootBlock[0x01] = 0x00000000			# unCtrl
	aBootBlock[0x02] = ulExecAddress		# execution address
	aBootBlock[0x03] = ulApplicationChecksum	# application checksum
	aBootBlock[0x04] = ulApplicationSize/4		# application dword size
	aBootBlock[0x05] = ulLoadAddress		# load address
	aBootBlock[0x06] = 0x5854454e			# 'NETX' signature
	aBootBlock[0x07] = 0x00000000			# krams
	aBootBlock[0x08] = 0x00000000			# krams
	aBootBlock[0x09] = 0x00000000			# krams
	aBootBlock[0x0a] = 0x00000000			# krams
	aBootBlock[0x0b] = 0x00000000			# krams
	aBootBlock[0x0c] = 0x00000001			# misc_asic_ctrl dummy
	aBootBlock[0x0d] = 0x00000000			# user data
	aBootBlock[0x0e] = 0x00000000			# src type
	
	# Test if we need to read the xml file.
	if isinstance(env['BOOTBLOCK_SRC'], str) or isinstance(env['BOOTBLOCK_DST'], str):
		# TODO: Read the xml file.
		raise Exception("read xml not done yet.")
	
	# Apply source options.
	if isinstance(env['BOOTBLOCK_SRC'], dict):
		for offset,value in env['BOOTBLOCK_SRC'].iteritems():
			uiOffset = long(offset)
			ulValue = long(value)
			if uiOffset<0 or uiOffset>16:
				raise Exception('invalid offset in BOOTBLOCK_SRC parameters: %s' % uiOffset)
			aBootBlock[uiOffset] = ulValue
	elif isinstance(env['BOOTBLOCK_SRC'], str):
		# TODO: Read the xml file.
		raise Exception("xml parameter not done yet.")
	else:
		raise Exception('The parameter BOOTBLOCK_SRC has an invalid type (%s), only dict and str can be processed.' % repr(type(env['BOOTBLOCK_SRC'])))
	
	# Apply destination options.
	if isinstance(env['BOOTBLOCK_DST'], dict):
		for offset,value in env['BOOTBLOCK_DST'].iteritems():
			uiOffset = long(offset)
			ulValue = long(value)
			if uiOffset<0 or uiOffset>16:
				raise Exception('invalid offset in BOOTBLOCK_DST parameters: %s' % uiOffset)
			aBootBlock[uiOffset] = ulValue
	elif isinstance(env['BOOTBLOCK_DST'], str):
		# TODO: Read the xml file.
		raise Exception("xml parameter not done yet.")
	else:
		raise Exception('The parameter BOOTBLOCK_DST has an invalid type (%s), only dict and str can be processed.' % repr(type(env['BOOTBLOCK_DST'])))
	
	# Build the bootblock checksum.
	ulBootblockChecksum = 0
	for ulData in aBootBlock:
		ulBootblockChecksum += ulData
		ulBootblockChecksum &= 0xffffffff
	ulBootblockChecksum = (ulBootblockChecksum-1)^0xffffffff
	aBootBlock[0x0f] = ulBootblockChecksum
	
	# Write the bootimage.
	fOutput = open(target[0].get_path(), 'wb')
	aBootBlock.tofile(fOutput)
	aulApplicationData.tofile(fOutput)
	fOutput.close()
	
	return None


def bootblock_emitter(target, source, env):
	# Make the target depend on the xml file and the parameter.
	Depends(target, env['BOOTBLOCK_XML'])
	Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_SRC']))
	Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_DST']))
	Depends(target, SCons.Node.Python.Value(env['BOOTBLOCK_USERDATA']))
	
	return target, source


def bootblock_string(target, source, env):
	return 'BootBlock %s' % target[0].get_path()


def ApplyToEnv(env):                                                                                                                                                                                            
	#----------------------------------------------------------------------------                                                                                                                           
	#                                                                                                                                                                                                       
	# Add secmem builder.                                                                                                                                                                                 
	#                                                                                                                                                                                                       
	env['BOOTBLOCK_XML'] = 'site_scons/netx.xml'
	env['BOOTBLOCK_SRC'] = ''
	env['BOOTBLOCK_DST'] = ''
	env['BOOTBLOCK_USERDATA'] = 0
	
	bootblock_act = SCons.Action.Action(bootblock_action, bootblock_string)
	bootblock_bld = Builder(action=bootblock_act, emitter=bootblock_emitter, suffix='.bin', single_source=1, src_suffix='.elf', src_builder='Elf')
	env['BUILDERS']['BootBlock'] = bootblock_bld

