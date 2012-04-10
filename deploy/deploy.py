# -*- coding: utf-8 -*-


import argparse
import hashlib
import httplib2
import os.path
import re
import xml.dom.minidom


import deploy_version
import repository_driver_nexus
import rest_driver_httplib
import rest_driver_httplib2


from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import XML


REVISION_SNAPSHOT = 0
REVISION_MAJOR    = 1
REVISION_MINOR    = 2


class Deploy:
	def __init__(self, strHost):
		# Create the rest driver.
		#tRestDriver = rest_driver_httplib.RestDriver()
		tRestDriver = rest_driver_httplib2.RestDriver()

		# Create the repository driver.
		self.tRepositoryDriver = repository_driver_nexus.RepositoryDriver(tRestDriver, strHost)

		# No Artifacts yet.
		self.aArtifacts = dict({})



	def to_bool(self, value):
		if str(value).lower() in ("yes", "y", "true",  "t", "1"):
			return True
		if str(value).lower() in ("no",  "n", "false", "f", "0"):
			return False
		raise Exception('Invalid value for boolean conversion: ' + str(value))



	def read_xml(self, strFileName):
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
			bSelected = self.to_bool(strValue.strip())
			aAttrib['selected'] = bSelected

			strValue = tNode.get('deploy_as', '0.0.0')
			strDeployAs = deploy_version.version(strValue.strip())
			aAttrib['deploy_as'] = strDeployAs

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
				bMatch = self.to_bool(tVersionNode.get('match'))
				aVersions[strVersion] = bMatch
			aAttrib['versions'] = aVersions

			strKey = '%s.%s' % (strGroupID, strArtifactID)
			if strKey in aArtifacts:
				raise Exception('Double key %s!' % strKey)
			aArtifacts[strKey] = aAttrib

		self.aArtifacts = aArtifacts


	def write_xml(self, strFileName):
		tXml = xml.dom.minidom.getDOMImplementation().createDocument(None, "Artifacts", None)
		tNode_Project = tXml.documentElement.appendChild(tXml.createElement('Project'))
		tNode_Targets = tNode_Project.appendChild(tXml.createElement('Targets'))

		# Loop over all artifacts.
		for aAttrib in self.aArtifacts.itervalues():
			tNode_Target = tNode_Targets.appendChild(tXml.createElement('Target'))
			tNode_Target.setAttribute('file', aAttrib['file'])
			tNode_Target.setAttribute('selected', str(aAttrib['selected']))
			tNode_Target.setAttribute('deploy_as', str(aAttrib['deploy_as']))

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


	def execute_scan(self):
		sizArtifacts = len(self.aArtifacts)
		print 'Found %d artifacts.' % sizArtifacts

		# Process all Target nodes.
		sizArtifactCnt = 0
		for tArtifact in self.aArtifacts.itervalues():
			sizArtifactCnt += 1
			print 'Processing artifact %d/%d (%d%%)' % (sizArtifactCnt, sizArtifacts, sizArtifactCnt*100/sizArtifacts)

			# Get all revisions of the artifact.
			atGAVersions = self.tRepositoryDriver.getAllArtifactVersions(tArtifact['gid'], tArtifact['aid'])

			# Get all repository versions with the same SHA1 sum.
			atSha1Versions = self.tRepositoryDriver.findSha1Artifacts(tArtifact['file'], tArtifact['gid'], tArtifact['aid'])

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


	def filter_init_all(self):
		for tArtifact in self.aArtifacts.itervalues():
			tArtifact['filter'] = True


	def filter_init_changed(self):
		tVersionSnapshot = deploy_version.version(0, 0, 0)
		for tArtifact in self.aArtifacts.itervalues():
			bSelected = True
			# Loop over all versions.
			for (strVersion,bMatch) in tArtifact['versions'].iteritems():
				tVersion = deploy_version.version(strVersion)
				if tVersion!=tVersionSnapshot and bMatch==True:
					bSelected = False
					break
			tArtifact['filter'] = bSelected


	def artifacts_filter(self, strFilter):
		# Compile the regular expression.
		tRegEx = re.compile(strFilter)

		# Loop over all artifacts.
		for tArtifact in self.aArtifacts.itervalues():
			# Only consider selected items.
			if tArtifact['filter']==True:
				# Combine the group and artifact ID into one string.
				strName = '%s.%s' % (tArtifact['gid'], tArtifact['aid'])
				tMatch = tRegEx.search(strName)
				if tMatch==None:
					tArtifact['filter'] = False


	def artifacts_filter_apply(self, strVersion):
		# Loop over all artifacts.
		for tArtifact in self.aArtifacts.itervalues():
			# Only consider selected items.
			if tArtifact['filter']==True:
				# This artifact will be deployed.
				tArtifact['selected'] = True
				# Set the version.
				if strVersion=='MAJ':
					# Get the latest version.
					tDeployVersion = deploy_version.version(0, 0, 0)
					for strVersion in tArtifact['versions'].iterkeys():
						tVersion = deploy_version.version(strVersion)
						if tVersion>tDeployVersion:
							tDeployVersion = tVersion
					tDeployVersion.next_major()
				elif strVersion=='MIN':
					# Get the latest version.
					tDeployVersion = deploy_version.version(0, 0, 0)
					for strVersion in tArtifact['versions'].iterkeys():
						tVersion = deploy_version.version(strVersion)
						if tVersion>tDeployVersion:
							tDeployVersion = tVersion
					tDeployVersion.next_minor()
				elif strVersion=='SNAPSHOT':
					tDeployVersion = deploy_version.version(0, 0, 0)
				else:
					tDeployVersion = deploy_version.version(strVersion)

				tArtifact['deploy_as'] = tDeployVersion

				# Processed.
				tArtifact['filter'] = False


	def execute_report(self):
		# Loop over all artifacts.
		for tArtifact in self.aArtifacts.itervalues():
			# Only consider selected items.
			if tArtifact['selected']==True:
				print '%s.%s : %s' % (tArtifact['gid'], tArtifact['aid'], str(tArtifact['deploy_as']))


	def execute_deploy(self):
		# Loop over all artifacts.
		for tArtifact in self.aArtifacts.itervalues():
			# Only consider selected items.
			if tArtifact['selected']==True:
				self.tRepositoryDriver.deploy(tArtifact)



def parse_version(strArgument):
	# Is this one of the special keywords?
	if strArgument.upper() in ['MAJ', 'MIN', 'SNAPSHOT']:
		# Ok, this is one of the special names.
		strResult = strArgument.upper()
	else:
		strResult = str(deploy_version.version(strArgument))

	return strResult



def main():
	tParser = argparse.ArgumentParser(description='Deploy some artifacts.')
	tParser.add_argument('--scan', action='store_true', dest='bScan', default=False,
	                     help='Scan the repository for existing versions of all artifacts and matching SHA1 checksums. Please note that all previously selected deploy versions are cleared.')
	tParser.add_argument('--select', choices=['none', 'all', 'changed'], dest='strSelect', default='none',
	                     help='Lalala.')
	tParser.add_argument('--filter', action='append', dest='aFilter', metavar='REGEX',
	                     help='Select all matching artifacts for deploy. Matching is done with a regular expression REGEX against the combination of the artifact group and name.')
	tParser.add_argument('--set', type=parse_version, dest='strVersion', metavar='VERSION', default='SNAPSHOT',
	                     help='Set the version of all filtered artifacts. The version can be MAJ, MIN, SNAPSHOT or an complete version string.')
	tParser.add_argument('--report', action='store_true', dest='bReport', default=False,
	                     help='Print a list of all artifacts wich will be deployed.')
	tParser.add_argument('--deploy', action='store_true', dest='bDeploy', default=False,
	                     help='Deploy all selected artifacts.')
	tParser.add_argument('-v', '--verbose', action='store_true', dest='bVerbose', default=False,
	                     help='Be verbose.')
	tParser.add_argument('-i', '--input', dest='strInputFileName', default='targets/artifacts.xml',
	                     help='read the XML from FILENAME', metavar='FILENAME')
	tParser.add_argument('-o', '--output', dest='strOutputFileName', default='targets/artifacts.xml',
	                     help='write the XML to FILENAME instead of stdout', metavar='FILENAME')
	aOptions = tParser.parse_args()

	print 'Welcome to deploy V1.0, written by Christoph Thelen in 2012.'

	tDeploy = Deploy('nexus.netx01.hilscher.local')

	# Read the artifact list.
	aArtifacts = tDeploy.read_xml(aOptions.strInputFileName)

	if aOptions.bScan==True:
		tDeploy.execute_scan()

	if aOptions.strSelect=='changed' or aOptions.strSelect=='all' or aOptions.aFilter!=None:
		# Init the filter list.
		if aOptions.strSelect=='changed':
			tDeploy.filter_init_changed()
		else:
			tDeploy.filter_init_all()

		# Loop over all filter elements.
		if aOptions.aFilter!=None:
			for strFilter in aOptions.aFilter:
				tDeploy.artifacts_filter(strFilter)

		# Add the filtered artifacts to the selection.
		tDeploy.artifacts_filter_apply(aOptions.strVersion)


	if aOptions.bReport==True:
		tDeploy.execute_report()

	if aOptions.bDeploy==True:
		tDeploy.execute_deploy()

	# Write the new XML tree.
	tDeploy.write_xml(aOptions.strOutputFileName)




if __name__ == '__main__':
	main()

