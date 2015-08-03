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
#import xml.etree.ElementTree

# NOTE: this is only for debug.
import datetime


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
	aCmd = [env['READELF'], '--symbols', '--wide', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]

	atSymbols = dict({})
	
	reSymbol = re.compile('\s+\d+:\s([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+\w+\s+GLOBAL\s+\w+\s+\d+\s+([\S]+)')

	for strLine in strOutput.split(os.linesep):
		tObj = reSymbol.match(strLine)
		if not tObj is None:
			ulValue = long(tObj.group(1), 16)
			strName = tObj.group(2)
			atSymbols[strName] = ulValue
	
	return atSymbols



def get_debug_structure(env, strFileName):
	aCmd = [env['READELF'], '--debug-dump=info', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]
	
	time_start = datetime.datetime.now()
	
	# Add all information to an XML file.
	#tRoot = xml.etree.ElementTree.Element('DebugInfo')
	#tXml = xml.etree.ElementTree.ElementTree(tRoot)
	atDebugInfo = dict({'name': None, 'abbrev': None, 'children': [], 'attributes': dict({})})
	
	# Prepare the regular expressions for the elements.
	reElement = re.compile('\s+<([0-9]+)><([0-9a-f]+)>: Abbrev Number: (\d+) \(DW_TAG_(\w+)\)')
	reAttribute_Str = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+\(indirect string, offset: 0x[0-9a-f]+\):\s+(.+)')
	reAttribute_Link = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+<0x([0-9a-f]+)>')
	reAttribute = re.compile('\s+<([0-9a-f]+)>\s+DW_AT_(\w+)\s*:\s+(.+)')
	
	# This is a list of all parent nodes. It supports a maximum depth of 64.
	atParentNode = []
	atParentNode.append(atDebugInfo)
	
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
			if uiNodeLevel<0 or uiNodeLevel>=len(atParentNode):
				raise Exception('Invalid node level: %d', uiNodeLevel)
			tParentNode = atParentNode[uiNodeLevel]
			if tParentNode is None:
				raise Exception('Invalid parent!')

			# This is a new element. Clear all parents above the parent.
			atParentNode = atParentNode[0:uiNodeLevel+1]
			
			# Create the new element.
			#tNode = xml.etree.ElementTree.SubElement(tParentNode, strName)
			#tNode.set('id', str(ulNodeId))
			#tNode.set('abbrev', str(ulAbbrev))
			atNodeData = dict({'name': strName, 'id': ulNodeId, 'attributes': dict({'abbrev': ulAbbrev}), 'children': []})
			tParentNode['children'].append(atNodeData)
			
			# Append the new element to the list of parent elements.
			atParentNode.append(atNodeData)
		else:
			tObj = reAttribute_Link.match(strLine)
			if not tObj is None:
				ulNodeId = int(tObj.group(1), 16)
				strName = tObj.group(2)
				ulValue = int(tObj.group(3), 16)
				tNode = atParentNode[-1]
				tNode['attributes'][strName] = ulValue
			else:
				tObj = reAttribute_Str.match(strLine)
				if tObj is None:
					tObj = reAttribute.match(strLine)
				
				if not tObj is None:
					ulNodeId = int(tObj.group(1), 16)
					strName = tObj.group(2)
					strValue = tObj.group(3).strip()
					tNode = atParentNode[-1]
					tNode['attributes'][strName] = strValue
	
	time_end = datetime.datetime.now()
	print 'Time used:', str(time_end-time_start)

#	# Write the XML tree to a test file.
#	astrXml = xml.etree.ElementTree.tostringlist(tXml.getroot(), encoding='UTF-8', method="xml")
#	tFile = open('/tmp/test.xml', 'wt')
#	tFile.write('\n'.join(astrXml))
#	tFile.close()
	
	return atDebugInfo



s_reLocation = re.compile('\d+ byte block: \d+ ([0-9a-f]+)')

def __iter_debug_info(tNode, atSymbols):
	strName = tNode['name']
	tAttr = tNode['attributes']
	
	# Is this an enumerator type?
	if strName=='enumerator':
		if not 'const_value' in tAttr:
			raise Exception('Missing const_value')
		if not 'name' in tAttr:
			raise Exception('Missing name')
		
		
		ulValue = int(tAttr['const_value'])
		strName = tAttr['name']
		atSymbols[strName] = ulValue
	elif strName=='structure_type':
		if 'name' in tAttr:
			strStructureName = tAttr['name']
			# Generate a symbol with the size of the structure.
			strMemberName = 'SIZEOF_' + strStructureName
			atSymbols[strMemberName] = tAttr['byte_size']
			# Generate symbols for the offset of each member.
			for tMember in tNode['children']:
				if tMember['name']=='member':
					tMemberAttr = tMember['attributes']
					strLoc = tMemberAttr['data_member_location']
					strName = tMemberAttr['name']
					if (not strLoc is None) and (not strName is None):
						tObj = s_reLocation.match(strLoc)
						if not tObj is None:
							strMemberName = 'OFFSETOF_' + strStructureName + '_' + strName
							ulOffset = int(tObj.group(1), 16)
							atSymbols[strMemberName] = ulOffset
	else:
		for tChild in tNode['children']:
			__iter_debug_info(tChild, atSymbols)



def get_debug_symbols(env, strFileName):
	atDebugInfo = get_debug_structure(env, strFileName)
	atAllSymbols = dict({})
	__iter_debug_info(atDebugInfo, atAllSymbols)
	return atAllSymbols



def get_macro_definitions(env, strFileName):
	aCmd = [env['READELF'], '--debug-dump=macro', strFileName]
	proc = subprocess.Popen(aCmd, stdout=subprocess.PIPE)
	strOutput = proc.communicate()[0]

	time_start = datetime.datetime.now()
	
	# All macros are collected in this dict.
	atMergedMacros = dict({})
	
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
				
				# Does the macro already exist?
				if strName in atMergedMacros:
					# Yes, it exists already. Is the value the same?
					if not(atMergedMacros[strName] is None) and (atMergedMacros[strName]!=strValue):
						# The macro exists more than one time with different values. Now that's a problem.
						atMergedMacros[strName] = None
				else:
					atMergedMacros[strName] = strValue
	
	time_end = datetime.datetime.now()
	print 'Time used:', str(time_end-time_start)

	return atMergedMacros



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

