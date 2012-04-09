# -*- coding: utf-8 -*-


import hashlib
import httplib2
import optparse
import os.path
import sys
import xml.dom.minidom


import deploy_version
import repository_driver_nexus
import rest_driver_httplib2


from string import Template
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import XML


REVISION_SNAPSHOT = 0
REVISION_MAJOR    = 1
REVISION_MINOR    = 2


def generate_pom(strSrcPath, strGroupID, strArtifactID, strPackaging, strRevision):
	aSubstitute = dict({
		'GROUP_ID': strGroupID,
		'ARTIFACT_ID' : strArtifactID,
		'VERSION' : strRevision,
		'PACKAGING' : strPackaging
	})
	
	strTemplate = '''<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
	<modelVersion>4.0.0</modelVersion>

	<groupId>${GROUP_ID}</groupId>
	<artifactId>${ARTIFACT_ID}</artifactId>
	<version>${VERSION}</version>
	<packaging>${PACKAGING}</packaging>
</project>
'''
	
	tTemplate = Template(strTemplate)
	return tTemplate.safe_substitute(aSubstitute)


def read_xml(strFileName):
	# Read the artifact list.
	tXml = ElementTree()
	tXml.parse(strFileName)

	aArtifacts = dict({})

	for tNode in tXml.findall('Project/Targets/Target'):
		aAttrib = dict({})
		strValue = tNode.get('file')
		if strValue==None:
			raise Exception('One of the Target nodes has no file attribute!')
		else:
			strFile = strValue.strip()
			if strFile=='':
				raise Exception('One of the Target nodes has an empty file attribute!')
			aAttrib['file'] = strFile

		strValue = tNode.get('selected', 'False')
		bSelected = bool(strValue.strip())
		aAttrib['selected'] = bSelected

		strValue = tNode.findtext('ArtifactID')
		if strValue==None:
			raise Exception('One of the Target nodes has no ArtifactID child!')
		else:
			strArtifactID = strValue.strip()
			if strArtifactID=='':
				raise Exception('One of the Target nodes has an empty ArtifactID child!')
			aAttrib['aid'] = strArtifactID

		strValue = tNode.findtext('GroupID')
		if strValue==None:
			raise Exception('One of the Target nodes has no GroupID child!')
		else:
			strGroupID = strValue.strip()
			if strGroupID=='':
				raise Exception('One of the Target nodes has an empty GroupID child!')
			aAttrib['gid'] = strGroupID

		strValue = tNode.findtext('Packaging')
		if strValue==None:
			raise Exception('One of the Target nodes has no Packaging child!')
		else:
			strPackaging = strValue.strip()
			if strPackaging=='':
				raise Exception('One of the Target nodes has an empty Packaging child!')
			aAttrib['packaging'] = strPackaging

		# Read all versions.
		aVersions = dict({})
		for tVersionNode in tNode.findall('version'):
			strVersion = tVersionNode.text.strip()
			if strVersion=='':
				raise Exception('One of the Target nodes has an empty version child!')
			if strVersion in aVersions:
				raise Exception('Double version!')
			bMatch = bool(tVersionNode.get('match'))
			aVersions[strVersion] = bMatch
		aAttrib['versions'] = aVersions

		strKey = '%s.%s' % (strGroupID, strArtifactID)
		if strKey in aArtifacts:
			raise Exception('Double key %s!' % strKey)
		aArtifacts[strKey] = aAttrib

	return aArtifacts


def write_xml(strFileName, aArtifacts):
	tXml = xml.dom.minidom.getDOMImplementation().createDocument(None, "Artifacts", None)
	tNode_Project = tXml.documentElement.appendChild(tXml.createElement('Project'))
	tNode_Targets = tNode_Project.appendChild(tXml.createElement('Targets'))

	# Loop over all artifacts.
	for aAttrib in aArtifacts.itervalues():
		tNode_Target = tNode_Targets.appendChild(tXml.createElement('Target'))
		tNode_Target.setAttribute('file', aAttrib['file'])
		tNode_Target.setAttribute('selected', str(aAttrib['selected']))

		# Create ArtifactID, GroupID and Packaging children.
		tNode_ArtifactID = tNode_Target.appendChild(tXml.createElement('ArtifactID'))
		tNode_ArtifactID.appendChild(tXml.createTextNode(aAttrib['aid']))

		tNode_GroupID = tNode_Target.appendChild(tXml.createElement('GroupID'))
		tNode_GroupID.appendChild(tXml.createTextNode(aAttrib['gid']))

		tNode_Packaging = tNode_Target.appendChild(tXml.createElement('Packaging'))
		tNode_Packaging.appendChild(tXml.createTextNode(aAttrib['packaging']))

		# Loop over all versions.
		for (strVersion,bMatch) in aAttrib['versions'].iteritems():
			tNode_Version = tNode_Target.appendChild(tXml.createElement('version'))
			tNode_Version.setAttribute('match', str(bMatch))
			tNode_Version.appendChild(tXml.createTextNode(strVersion))

	# Write the file.
	tFile = open(strFileName, 'wt')
	tXml.writexml(tFile, indent='', addindent='\t', newl='\n', encoding='UTF-8')
	tFile.close()


def execute_scan(aArtifacts):
	# Create the rest driver for httplib2.
	tRestDriver = rest_driver_httplib2.RestDriver()

	# Create the repository driver.
	tRepository = repository_driver_nexus.RepositoryDriver(tRestDriver, 'http://nexus.netx01.hilscher.local/')

	sizArtifacts = len(aArtifacts)
	print 'Found %d artifacts.' % sizArtifacts

	# Process all Target nodes.
	sizArtifactCnt = 0
	for tArtifact in aArtifacts.itervalues():
		sizArtifactCnt += 1
		print 'Processing artifact %d/%d (%d%%)' % (sizArtifactCnt, sizArtifacts, sizArtifactCnt*100/sizArtifacts)

		# Get all revisions of the artifact.
		atGAVersions = tRepository.getAllArtifactVersions(tArtifact['gid'], tArtifact['aid'])

		# Get all repository versions with the same SHA1 sum.
		atSha1Versions = tRepository.findSha1Artifacts(tArtifact['file'], tArtifact['gid'], tArtifact['aid'])

		# Sanity test: all matching versions must also exist.
		for tVersion in atSha1Versions:
			if not tVersion in atGAVersions:
				raise Exception('Artifact %s.%s: version %s does not exist!' % (strGroupID, strArtifactID, str(tVersion)))

		# Add the revision information to the node.
		aVersions = dict({})
		for tVersion in atGAVersions:
			bMatch = tVersion in atSha1Versions
			aVersions[str(tVersion)] = bMatch

		tArtifact['versions'] = aVersions


def main(argv):
	tParser = optparse.OptionParser(usage='usage: %prog [options] imagefile')
	tParser.add_option('--scan', action='store_true', dest='bScan', default=False,
	                  help='Scan the repository for existing versions of all artifacts and matching SHA1 checksums. Please note that all previously selected deploy versions are cleared.')
	tParser.add_option('--redeploy', action='store_true', dest='bRedeploy', default=False,
	                  help='Without this switch the select operation considers only artifacts which are not deployed yet. This option uses all artifacts, even if they are already present in the repository.')
	tParser.add_option('--select REGEX', action='append', dest='aSelect',
	                  help='Select all matching artifacts for deploy. Matching is done with a regular expression REGEX against the combination of the artifact group and name.')
	tParser.add_option('--report', action='store_true', dest='bReport', default=False,
	                  help='Print a list of all artifacts wich will be deployed.')
	tParser.add_option('--deploy', action='store_true', dest='bDeploy', default=False,
	                  help='Deploy all selected artifacts.')
	tParser.add_option('-v', '--verbose', action='store_true', dest='bVerbose', default=False,
	                  help='Be verbose.')
	tParser.add_option('-o', '--output', type='string', dest='strOutputFileName', default='targets/artifacts2.xml',
	                  help='write the XML to FILENAME instead of stdout', metavar='FILENAME')
	(aOptions, aArgs) = tParser.parse_args()

	print 'Welcome to deploy V1.0, written by Christoph Thelen in 2012.'
	print 'bScan = ' + str(aOptions.bScan)
	print 'bRedeploy = ' + str(aOptions.bRedeploy)
	if aOptions.aSelect!=None:
		for strSelect in aOptions.aSelect:
			print 'select = ' + strSelect
	print 'bReport = ' + str(aOptions.bReport)
	print 'bDeploy = ' + str(aOptions.bDeploy)
	print 'bVerbose = ' + str(aOptions.bVerbose)
	print 'strOutputFileName = ' + str(aOptions.strOutputFileName)

	# Read the artifact list.
	aArtifacts = read_xml('targets/artifacts.xml')

	if aOptions.bScan==True:
		execute_scan(aArtifacts)

	if aOptions.aSelect!=None:
		for strSelect in aOptions.aSelect:
			print 'select = ' + strSelect
	
	# Write the new XML tree.
	write_xml(aOptions.strOutputFileName, aArtifacts)




if __name__ == '__main__':
	main(sys.argv[1:])

