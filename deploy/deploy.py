# -*- coding: utf-8 -*-


import hashlib
import httplib2
import optparse
import os.path
import sys


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


def execute_scan(tXml):
	# Create the rest driver for httplib2.
	tRestDriver = rest_driver_httplib2.RestDriver()

	# Create the repository driver.
	tRepository = repository_driver_nexus.RepositoryDriver(tRestDriver, 'http://nexus.netx01.hilscher.local/')

	atAllTargetNodes = tXml.findall('Project/Targets/Target')
	sizAllTargetNodes = len(atAllTargetNodes)
	print 'Found %d artifacts.' % sizAllTargetNodes

	# Process all Target nodes.
	sizNodeCnt = 0
	for tNode in atAllTargetNodes:
		sizNodeCnt += 1
		print 'Processing artifact %d/%d (%d%%)' % (sizNodeCnt, sizAllTargetNodes, sizNodeCnt*100/sizAllTargetNodes)
		strValue = tNode.get('file')
		if strValue==None:
			raise Exception('One of the Target nodes has no file attribute!')
		else:
			strFile = strValue.strip()
			if strFile=='':
				raise Exception('One of the Target nodes has an empty file attribute!')

		strValue = tNode.findtext('ArtifactID')
		if strValue==None:
			raise Exception('One of the Target nodes has no ArtifactID child!')
		else:
			strArtifactID = strValue.strip()
			if strArtifactID=='':
				raise Exception('One of the Target nodes has an empty ArtifactID child!')

		strValue = tNode.findtext('GroupID')
		if strValue==None:
			raise Exception('One of the Target nodes has no GroupID child!')
		else:
			strGroupID = strValue.strip()
			if strGroupID=='':
				raise Exception('One of the Target nodes has an empty GroupID child!')

		strValue = tNode.findtext('Packaging')
		if strValue==None:
			raise Exception('One of the Target nodes has no Packaging child!')
		else:
			strPackaging = strValue.strip()
			if strPackaging=='':
				raise Exception('One of the Target nodes has an empty Packaging child!')


		# Get all revisions of the artifact.
		atGAVersions = tRepository.getAllArtifactVersions(strGroupID, strArtifactID)

		# Get all repository versions with the same SHA1 sum.
		atSha1Versions = tRepository.findSha1Artifacts(strFile, strGroupID, strArtifactID)

		# Add the revision information to the node.
		for tVersion in atGAVersions:
			tSubElem = SubElement(tNode, 'version')
			tSubElem.text = str(tVersion)
			bMatch = tVersion in atSha1Versions
			tSubElem.set('match', str(bMatch))


		# Sanity test: all matching versions must also exist.
		for tVersion in atSha1Versions:
			if not tVersion in atGAVersions:
				raise Exception('Artifact %s.%s: version %s does not exist!' % (strGroupID, strArtifactID, str(tVersion)))



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
	tXml = ElementTree()
	tXml.parse('targets/artifacts.xml')

	if aOptions.bScan==True:
		execute_scan(tXml)

	# Write the new XML tree.
	tXml.write(aOptions.strOutputFileName, encoding="UTF-8", xml_declaration=True, method="xml")




if __name__ == '__main__':
	main(sys.argv[1:])

