# -*- coding: utf-8 -*-

from SCons.Script import *
from string import Template

import os.path
import xml.dom.minidom


aArtifacts = dict({})


def add_artifact(tEnv, tFiles, strGroupID, strArtifactID, strPackaging):
	# Process all files.
	for tFile in tFiles:
		print 'AddArtifact %s' % tFile.get_path()
		
		if not strGroupID in aArtifacts:
			aArtifacts[strGroupID] = dict({})

		aGroups = aArtifacts[strGroupID]
		if strArtifactID in aGroups:
			raise Exception('Double defined artifact "%s" in group "%s"!'%(strArtifactID, strGroupID))

		aGroups[strArtifactID] = dict({
			'file': tFile,
			'packaging': strPackaging
		})


def artifact_action(target, source, env):
	tXmlData = xml.dom.minidom.getDOMImplementation().createDocument(None, "Artifacts", None)
	tNode_Project = tXmlData.documentElement.appendChild(tXmlData.createElement('Project'))
	tNode_Targets = tNode_Project.appendChild(tXmlData.createElement('Targets'))

	# Loop over all artifacts.
	for (strGroupID,atFiles) in aArtifacts.items():
		for (strArtifactID,tFileAttribs) in atFiles.items():
			# Create a new Target node with the path to the file as
			# 'file' attribute.
			tNode_Target = tNode_Targets.appendChild(tXmlData.createElement('Target'))
			tNode_Target.setAttribute('file', tFileAttribs['file'].get_path())
			# Create ArtifactID, GroupID and Packaging children.
			tNode_ArtifactID = tNode_Target.appendChild(tXmlData.createElement('ArtifactID'))
			tNode_ArtifactID.appendChild(tXmlData.createTextNode(strArtifactID))
			tNode_GroupID = tNode_Target.appendChild(tXmlData.createElement('GroupID'))
			tNode_GroupID.appendChild(tXmlData.createTextNode(strGroupID))
			tNode_Packaging = tNode_Target.appendChild(tXmlData.createElement('Packaging'))
			tNode_Packaging.appendChild(tXmlData.createTextNode(tFileAttribs['packaging']))

	# Write the file to the target.
	tFile = open(target[0].get_path(), 'wt')
	tXmlData.writexml(tFile, indent='', addindent='\t', newl='\n', encoding='UTF-8')
	tFile.close()

	return None


def artifact_emitter(target, source, env):
	# Loop over all elements in the 'aArtifacts' dictionary and make the
	# target depend on them.
	for (strGroupID,atFiles) in aArtifacts.items():
		for (strArtifactID,tFileAttribs) in atFiles.items():
			Depends(target, tFileAttribs['file'])

	return target, source


def artifact_string(target, source, env):
	return 'Artifact %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add artifact builder.
	#

	# Init the filename->revision dictionary.
	aArtifacts = dict({})

	artifact_act = SCons.Action.Action(artifact_action, artifact_string)
	artifact_bld = Builder(action=artifact_act, emitter=artifact_emitter, suffix='.xml')
	# TODO: Do not add the ArtifactInt builder to the global list.
	env['BUILDERS']['Artifact'] = artifact_bld

	# Provide the 'Artifact' method.
	env.AddMethod(add_artifact, 'AddArtifact')
