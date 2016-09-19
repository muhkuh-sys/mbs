# -*- coding: utf-8 -*-


import hboot_image_compiler.hboot_image

import os.path
import xml.dom.minidom
import xml.etree.ElementTree

from SCons.Script import *


def hboot_definition_scan(node, env, path):
	# This is the list of dependencies.
	atDependencies = []
	
	atKnownFiles = {}
	if 'HBOOTIMAGE_KNOWN_FILES' in env:
		atKnownFiles = env['HBOOTIMAGE_KNOWN_FILES']
	
	# Get the contents of the XML file.
	strXml = node.get_contents()
	# Ignore invalid XML files here.
	tXml = None
	try:
		tXml = xml.etree.ElementTree.fromstring(strXml)
	except xml.etree.ElementTree.ParseError:
		pass

	if not tXml is None:
		tRootName = tXml.tag
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
	if 'HBOOTIMAGE_KNOWN_FILES' in env:
		atKnownFiles = env['HBOOTIMAGE_KNOWN_FILES']

	strKeyRom = None
	if 'HBOOTIMAGE_KEYROM_XML' in env:
		strKeyRom = env['HBOOTIMAGE_KEYROM_XML']

	astrIncludePaths = None
	if 'HBOOTIMAGE_INCLUDE_PATHS' in env:
		atValues = env['HBOOTIMAGE_INCLUDE_PATHS']
		if atValues is not None and len(atValues)!=0:
			astrIncludePaths = []
			astrIncludePaths.extend(atValues)

	astrSnippetSearchPaths = None
	if len(env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS'])!=0:
		astrSnippetSearchPaths = []
		astrSnippetSearchPaths.extend(env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS'])

	fVerbose = False
	if 'HBOOTIMAGE_VERBOSE' in env:
		fVerbose = bool(env['HBOOTIMAGE_VERBOSE'])

	strPatchDefinition = env['HBOOTIMAGE_PATCH_DEFINITION']

	iChipTyp = env['BOOTBLOCK_CHIPTYPE']
	tCompiler = hboot_image_compiler.hboot_image.HbootImage(env, iChipTyp, strPatchDefinition, includes=astrIncludePaths, sniplibs=astrSnippetSearchPaths, known_files=atKnownFiles, keyrom=strKeyRom, verbose=fVerbose)
	tCompiler.parse_image(source[0].get_path())
	tCompiler.write(target[0].get_path())

	return 0



def hboot_image_emitter(target, source, env):
	if 'HBOOTIMAGE_KNOWN_FILES' in env:
		atKnownFiles = env['HBOOTIMAGE_KNOWN_FILES']
		if atKnownFiles is not None:
			for strId,strPath in atKnownFiles.items():
				# NOTE: Only add the reference here as a string.
				# The source scanner will check if this reference is really used.
				env.Depends(target, SCons.Node.Python.Value('%s:%s' % (strId,strPath)))

	if 'HBOOTIMAGE_KEYROM_XML' in env:
		tKeyrom = env['HBOOTIMAGE_KEYROM_XML']
		if tKeyrom is not None:
			env.Depends(target, tKeyrom)

	if 'HBOOTIMAGE_INCLUDE_PATHS' in env:
		astrIncludePaths = env['HBOOTIMAGE_INCLUDE_PATHS']
		if astrIncludePaths is not None and len(astrIncludePaths)!=0:
			env.Depends(target, SCons.Node.Python.Value(':'.join(astrIncludePaths)))

	if 'HBOOTIMAGE_SNIPLIB_SEARCHPATHS' in env:
		astrSnipLibs = env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS']
		if astrSnipLibs is not None and len(astrSnipLibs)!=0:
			env.Depends(target, SCons.Node.Python.Value(':'.join(astrSnipLibs)))

	strPatchDefinition = None
	if 'HBOOTIMAGE_PATCH_DEFINITION' in env:
		strPatchDefinition = env['HBOOTIMAGE_PATCH_DEFINITION']
	else:
		# Get the chip type.
		strRelPatchDefinition = None
		iChipTyp = env['BOOTBLOCK_CHIPTYPE']
		if iChipTyp == 4000:
			strRelPatchDefinition = 'hboot_netx4000_patch_table.xml'
		elif iChipTyp == 56:
			strRelPatchDefinition = 'hboot_netx56_patch_table.xml'
		else:
			raise Exception('Invalid chip type: "%s"'%iChipTyp)

		strPatchDefinition = os.path.join(os.path.dirname(os.path.abspath(__file__)), strRelPatchDefinition)
		env['HBOOTIMAGE_PATCH_DEFINITION'] = strPatchDefinition
	env.Depends(target, strPatchDefinition)

	fVerbose = False
	if 'HBOOTIMAGE_VERBOSE' in env:
		fVerbose = bool(env['HBOOTIMAGE_VERBOSE'])
	env.Depends(target, SCons.Node.Python.Value(str(fVerbose)))

	return target, source



def hboot_image_string(target, source, env):
	return 'HBootImage %s' % target[0].get_path()



def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add HBootImageNew builder.
	#
	env['HBOOTIMAGE_KNOWN_FILES'] = None
	env['HBOOTIMAGE_KEYROM_XML'] = None
	env['HBOOTIMAGE_INCLUDE_PATHS'] = None
	env['HBOOTIMAGE_SNIPLIB_SEARCHPATHS'] = ['mbs/sniplib', 'src/sniplib', 'targets/snippets']
	env['HBOOTIMAGE_VERBOSE'] = False

	hboot_image_act = SCons.Action.Action(hboot_image_action, hboot_image_string)
	hboot_image_scanner = SCons.Scanner.Scanner(function=hboot_definition_scan)
	hboot_image_bld = Builder(action=hboot_image_act, emitter=hboot_image_emitter, suffix='.xml', single_source=1, source_scanner=hboot_image_scanner)
	env['BUILDERS']['HBootImage'] = hboot_image_bld

