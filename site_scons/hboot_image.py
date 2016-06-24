# -*- coding: utf-8 -*-


import hboot_image_compiler

import os.path
import xml.dom.minidom
import xml.etree.ElementTree

from SCons.Script import *


def hboot_definition_scan(node, env, path):
	# This is the list of dependencies.
	atDependencies = []
	
	atKnownFiles = dict({})
	if 'KNOWN_FILES' in env:
		atKnownFiles = env['KNOWN_FILES']
	
	strPath = node.get_path()
	tXml = xml.etree.ElementTree.parse(strPath)
	tRootName = tXml.getroot().tag
	if tRootName=='HBootImage':
		# This is the definition of the boot image.
		# Look for all "name" attributes of "File" nodes.
		for tNode in tXml.findall('.//File[@name]'):
			strFileName = tNode.get('name')
			# Is this a reference?
			if strFileName[0]=='@':
				# Yes -> try to replace it with the known files.
				# Cut off the '@'.
				strFileId = strFileName[1:]
				if not strFileId in atKnownFiles:
					raise Exception('Unknown reference to file ID "%s".' % strFileName)
				strFile = atKnownFiles[strFileId]
			# Add the file to the dependencies.
			atDependencies.append(strFile)

	return atDependencies



def hboot_image_action(target, source, env):
	atKnownFiles = dict({})
	if 'KNOWN_FILES' in env:
		atKnownFiles = env['KNOWN_FILES']

	strKeyRom = None
	if 'KEYROM_XML' in env:
		strKeyRom = env['KEYROM_XML']
	
	tSource = None
	tPatchDefinition = None
	
	for tSrc in source:
		strSrcPath = tSrc.get_path()
		
		strPathRoot,strPathExt = os.path.splitext(strSrcPath)
		if strPathExt=='.xml':
			tXml = xml.dom.minidom.parse(strSrcPath)
			strRootTag = tXml.documentElement.localName
	                
			# All sources have the root node 'Options'.
			if strRootTag=='HBootImage':
				#print 'This is an options file.'
				tSource = tXml
			# The patch definition has the root node 'PatchDefinitions'.
			elif strRootTag=='PatchDefinitions':
				#print 'This is a patch definition.'
				if not tPatchDefinition is None:
					raise Exception('More than one patch definition specified!')
				tPatchDefinition = tXml
			else:
				raise Exception('Unknown root tag "%s" in file "%s".' % (strRootTag,strSrcPath))
		else:
			# This is not an XML file.
			raise Exception('Unknown input file "%s".' % strSrcPath)
	  
	if tSource is None:
		raise Exception('No source specified!')
	if tPatchDefinition is None:
		# No patch definition defined yet. Use the default definition.
		
		# Get the chip type.
		iChipTyp = env['BOOTBLOCK_CHIPTYPE']
		strPatchDefinition = None
		if iChipTyp==4000:
			strPatchDefinition = 'hboot_netx4000_patch_table.xml'
		else:
			raise Exception('Invalid chip type: "%s"'%iChipTyp)
		
		tPatchDefinition = os.path.join(os.path.dirname(os.path.abspath(__file__)), strPatchDefinition)

	tCompiler = hboot_image_compiler.HbootImage(env, strKeyRom)
	tCompiler.set_patch_definitions(tPatchDefinition)
	tCompiler.set_known_files(atKnownFiles)
	tCompiler.parse_image(tSource.documentElement)
	tCompiler.write(target[0].get_path())
	
	return 0



def hboot_image_emitter(target, source, env):
	if 'KNOWN_FILES' in env:
		for strId,strPath in env['KNOWN_FILES'].items():
			Depends(target, SCons.Node.Python.Value('%s:%s' % (strId,strPath)))
	
	if 'KEYROM_XML' in env:
		Depends(target, SCons.Node.Python.Value(env['KEYROM_XML']))
	
	return target, source



def hboot_image_string(target, source, env):
	return 'HBootImage %s' % target[0].get_path()



def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add HBootImageNew builder.
	#
	hboot_image_act = SCons.Action.Action(hboot_image_action, hboot_image_string)
	hboot_image_scanner = SCons.Scanner.Scanner(function=hboot_definition_scan)
	hboot_image_bld = Builder(action=hboot_image_act, emitter=hboot_image_emitter, suffix='.xml', source_scanner=hboot_image_scanner)
	env['BUILDERS']['HBootImage'] = hboot_image_bld

