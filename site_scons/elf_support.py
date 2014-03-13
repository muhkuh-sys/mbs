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


import itertools
import os
import re
import subprocess
import xml.etree.ElementTree


def get_segment_table(env, strFileName):
	atSegments = []
	aCmd = [env['OBJDUMP'], '-h', '-w', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	for match_obj in re.finditer('[ \t]*([0-9]+)[ \t]+([^ \t]+)[ \t]+([0-9a-fA-F]+)[ \t]+([0-9a-fA-F]+)[ \t]+([0-9a-fA-F]+)[ \t]+([0-9a-fA-F]+)[ \t]+([0-9*]+)[ \t]+([a-zA-Z ,]+)', strOutput):
		uiAlign = eval(match_obj.group(7))
		astrFlags = match_obj.group(8).split(', ')
		atSegments.append(dict({
			'idx':		long(match_obj.group(1)),
			'name' :	match_obj.group(2),
			'size' :	long(match_obj.group(3),16),
			'vma' :		long(match_obj.group(4),16),
			'lma' :		long(match_obj.group(5),16),
			'file_off' :	long(match_obj.group(6),16),
			'align' :	uiAlign,
			'flags' :	astrFlags
		}))
	return atSegments



def get_symbol_table(env, strFileName):
	atSymbols = dict({})
	aCmd = [env['READELF'], '-s', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	for match_obj in re.finditer('[ \t]+[0-9]+\:[ \t]+([0-9a-fA-F]+)[ \t]+[0-9]+[ \t]+[A-Z]+[ \t]+[A-Z]+[ \t]+[A-Z]+[ \t]+[A-Z0-9]+[ \t]+([_a-zA-Z0-9]+)', strOutput):
		ulValue = int(match_obj.group(1), 16)
		strName = match_obj.group(2)
		atSymbols[strName] = ulValue
	return atSymbols



def get_debug_info(env, strFileName):
	aCmd = [env['READELF'], '--debug-dump=info', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	
	# Add all information to an XML file.
	tRoot = xml.etree.ElementTree.Element('DebugInfo')
	tXml = xml.etree.ElementTree.ElementTree(tRoot)
	
	# Prepare the regular expressions for the elements.
	reElement = re.compile('\s+<([0-9]+)><([0-9a-f]+)>: Abbrev Number: (\d+) \(DW_TAG_(\w+)\)')
	reAttribute_Str = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+\(indirect string, offset: 0x[0-9a-f]+\):\s+(.+)')
	reAttribute_Link = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+<0x([0-9a-f]+)>')
	reAttribute = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+(.+)')
	
	# This is a list of all parent nodes. It supports a maximum depth of 64.
	atParents = []
	atParents.append(tRoot)
	
	# Loop over all lines in the ".debug_info" section.
	for strLine in strOutput.split(os.linesep):
		# Is this a new element?
		tObj = reElement.match(strLine)
		if not tObj is None:
			uiNodeLevel = int(tObj.group(1))
			ulNodeId = int(tObj.group(2), 16)
			ulAbbrev = int(tObj.group(3))
			strName = tObj.group(4)
			
			# Get the parent node.
			if uiNodeLevel<0 or uiNodeLevel>=len(atParents):
				raise Exception('Invalid node level: %d', uiNodeLevel)
			tParentNode = atParents[uiNodeLevel]
			if tParentNode==0:
				raise Exception('Invalid parent!')
			
			# This is a new element. Clear all parents above the parent.
			atParents = atParents[0:uiNodeLevel+1]
			
			# Create the new element.
			tNode = xml.etree.ElementTree.SubElement(tParentNode, strName)
			tNode.set('id', str(ulNodeId))
			tNode.set('abbrev', str(ulAbbrev))
			
			# Append the new element to the list of parent elements.
			atParents.append(tNode)
		else:
			tObj = reAttribute_Link.match(strLine)
			if not tObj is None:
				ulNodeId = int(tObj.group(1), 16)
				strName = tObj.group(2)
				ulValue = int(tObj.group(3), 16)
				tNode = atParents[len(atParents)-1]
				tNode.set(strName, str(ulValue))
			else:
				tObj = reAttribute_Str.match(strLine)
				if tObj is None:
					tObj = reAttribute.match(strLine)
				
				if not tObj is None:
					ulNodeId = int(tObj.group(1), 16)
					strName = tObj.group(2)
					strValue = tObj.group(3).strip()
					tNode = atParents[len(atParents)-1]
					tNode.set(strName, strValue)
	
	
	aCmd = [env['READELF'], '--debug-dump=macro', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	
	# Add all macros here.
	tMacroRoot = xml.etree.ElementTree.SubElement(tRoot, 'MergedMacros')
	
	# FIXME: Macro extraction should respect different files.
	# NOTE: This matches only macros without parameter.
	areMacro = [
		re.compile('\s+DW_MACINFO_define - lineno : \d+ macro : (\w+)\s+(.*)'),
		re.compile('\s+DW_MACRO_GNU_define_indirect - lineno : \d+ macro : (\w+)\s+(.*)')
	]
	# Loop over all lines in the ".debug_macinfo" section.
	for strLine in strOutput.split(os.linesep):
		# Is this a new element?
		for reMacro in areMacro:
			tObj = reMacro.match(strLine)
			if not tObj is None:
				strName = tObj.group(1)
				strValue = tObj.group(2)
				tNode = xml.etree.ElementTree.SubElement(tMacroRoot, 'Macro')
				tNode.set('name', strName)
				tNode.set('value', strValue)
	
	
#	# Write the XML tree to a test file.
#	astrXml = xml.etree.ElementTree.tostringlist(tXml.getroot(), encoding='UTF-8', method="xml")
#	tFile = open('/tmp/test.xml', 'wt')
#	tFile.write(''.join(astrXml))
#	tFile.close()
	
	return tXml




def get_load_address(atSegments):
	# Set an invalid lma
	ulLowestLma = 0x100000000
	
	# Loop over all segments.
	for tSegment in atSegments:
		# Get the segment with the lowest 'lma' entry which has also the flags 'CONTENTS', 'ALLOC' and 'LOAD'.
		if (tSegment['lma']<ulLowestLma) and ('CONTENTS' in tSegment['flags']) and ('ALLOC' in tSegment['flags']) and ('LOAD' in tSegment['flags']):
			ulLowestLma = tSegment['lma']
	
	if ulLowestLma==0x100000000:
		raise Exception("failed to extract load address!")
	
	return ulLowestLma


def get_estimated_bin_size(atSegments):
	ulLoadAddress = get_load_address(atSegments)
	ulBiggestOffset = 0
	
	# Loop over all segments.
	for tSegment in atSegments:
		# Get the segment with the biggest offset to ulLoadAddress which has also the flags 'CONTENTS', 'ALLOC' and 'LOAD'.
		if ('CONTENTS' in tSegment['flags']) and ('ALLOC' in tSegment['flags']) and ('LOAD' in tSegment['flags']):
			ulOffset = tSegment['lma'] + tSegment['size'] - ulLoadAddress
			if ulOffset>ulBiggestOffset:
				ulBiggestOffset = ulOffset
	
	return ulBiggestOffset


def get_exec_address(env, strElfFileName):
	# Get the start address.
	aCmd = [env['OBJDUMP'], '-f', strElfFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	match_obj = re.search('start address 0x([0-9a-fA-F]+)', strOutput)
	if not match_obj:
		print 'Failed to extract start address.'
		print 'Command:', aCmd
		print 'Output:', strOutput
		raise Exception('Failed to extract start address.')
	
	return long(match_obj.group(1), 16)

