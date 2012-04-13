# -*- coding: utf-8 -*-


import argparse
import hashlib
import httplib2
import os.path
import re


import deploy_version
import repository_driver_nexus
#import rest_driver_httplib
import rest_driver_httplib2


import xml.etree.ElementTree


REVISION_SNAPSHOT = 0
REVISION_MAJOR    = 1
REVISION_MINOR    = 2


class Deploy:
	def __init__(self, strHost):
		# Create the rest driver.
		tRestDriver = rest_driver_httplib2.RestDriver()

		# Create the repository driver.
		self.tRepositoryDriver = repository_driver_nexus.RepositoryDriver(tRestDriver, strHost)

		# No credentials yet.
		self.aCredentials = dict({})



	def read_credentials(self, strConfigPath):
		strRealPath = os.path.abspath(os.path.expanduser(strConfigPath))
		if os.path.isfile(strRealPath)==True:
			tXml = xml.etree.ElementTree.ElementTree()
			tXml.parse(strRealPath)

			for tNode in tXml.findall('server'):
				strId = tNode.get('id')
				if strId==None:
					raise Exception('A server has no "id" attribute.')
				
				strValue = tNode.findtext('url')
				if strValue==None:
					raise Exception('Account "%s" has no "url" node.' % strId)
				strUrl = strValue.strip()
				if strUrl=='':
					raise Exception('Account "%s" has an empty "url" node.' % strId)

				strValue = tNode.findtext('user')
				if strValue==None:
					raise Exception('Account "%s" has no "user" node.' % strId)
				strUser = strValue.strip()
				if strUser=='':
					raise Exception('Account "%s" has an empty "user" node.' % strId)

				strValue = tNode.findtext('password')
				if strValue==None:
					raise Exception('Account "%s" has no "password" node.' % strId)
				strPassword = strValue.strip()
				if strPassword=='':
					raise Exception('Account "%s" has an empty "password" node.' % strId)

				aAttrib = dict({
					'url': strUrl,
					'user': strUser,
					'password': strPassword
				})

				self.aCredentials[strId] = aAttrib
                                print 'Credential %s: %s, %s' % (strId, strUrl, strUser)



	def set_credentials(self, strId):
		if not strId in self.aCredentials:
			raise Exception('Requested credentials "%s" not found!' % strId)

		self.tRepositoryDriver.set_credentials(self.aCredentials[strId])



	def to_bool(self, value):
		if str(value).lower() in ("yes", "y", "true",  "t", "1"):
			return True
		if str(value).lower() in ("no",  "n", "false", "f", "0"):
			return False
		raise Exception('Invalid value for boolean conversion: ' + str(value))



	def read_xml(self, strFileName):
		# Read the artifact list.
		self.tXml = xml.etree.ElementTree.ElementTree()
		self.tXml.parse(strFileName)



	def write_xml(self, strFileName):
		# Remove all 'filter' attributes. They are internal only.
		for tNodeTarget in self.tXml.findall('Project/Server/Target'):
			if 'filter' in tNodeTarget.attrib:
				del tNodeTarget.attrib['filter']

		# Convert the XML to a string.
		strXml = xml.etree.ElementTree.tostring(self.tXml.getroot(), encoding="us-ascii", method="xml")
		# Write the string to the destination file.
		tFile = open(strFileName, 'wt')
		tFile.write(strXml)
		tFile.close()



	def read_target_node(self, tNode):
		aAttrib = dict({})
		strValue = tNode.get('file')
		if strValue==None:
			raise Exception('One of the Target nodes has no file attribute!')
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
		strArtifactID = strValue.strip()
		if strArtifactID=='':
			raise Exception('One of the Target nodes has an empty ArtifactID child!')
		aAttrib['aid'] = strArtifactID

		strValue = tNode.findtext('GroupID')
		if strValue==None:
			raise Exception('One of the Target nodes has no GroupID child!')
		strGroupID = strValue.strip()
		if strGroupID=='':
			raise Exception('One of the Target nodes has an empty GroupID child!')
		aAttrib['gid'] = strGroupID

		strValue = tNode.findtext('Packaging')
		if strValue==None:
			raise Exception('One of the Target nodes has no Packaging child!')
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

		return aAttrib



	def execute_scan(self):
		sizArtifacts = len(self.tXml.findall('Project/Server/Target'))
		print 'Found %d artifacts.' % sizArtifacts

		# Process all Target nodes.
		sizArtifactCnt = 0
		for tNodeServer in self.tXml.findall('Project/Server'):
			# Get the server ID for all artifacts below.
			strServerID = tNodeServer.get('id')

			# Set the credentials for this server.
			self.set_credentials(strServerID)

			# Loop over all targets for this server.
			for tNodeTarget in tNodeServer.findall('Target'):
				# One more Artifact found.
				sizArtifactCnt += 1
				print 'Processing artifact %d/%d (%d%%)' % (sizArtifactCnt, sizArtifacts, sizArtifactCnt*100/sizArtifacts)

				tArtifact = self.read_target_node(tNodeTarget)

				# Get all revisions of the artifact.
				atGAVersions = self.tRepositoryDriver.getAllArtifactVersions(tArtifact['gid'], tArtifact['aid'])

				# Get all repository versions with the same SHA1 sum.
				atSha1Versions = self.tRepositoryDriver.findSha1Artifacts(tArtifact['file'], tArtifact['gid'], tArtifact['aid'])

				# Sanity test: all matching versions must also exist.
				for tVersion in atSha1Versions:
					if not tVersion in atGAVersions:
						raise Exception('Artifact %s.%s: version %s does not exist!' % (strGroupID, strArtifactID, str(tVersion)))

				# Deselect the node.
				tNodeTarget.set('selected', str(False))

				# Remove any old version nodes.
				for tVersionNode in tNodeTarget.findall('version'):
					tNodeTarget.remove(tVersionNode)

				# Add the revision information to the node.
				for tVersion in atGAVersions:
					bMatch = tVersion in atSha1Versions
					tNodeVersion = xml.etree.ElementTree.SubElement(tNodeTarget, 'version', attrib={'match': str(bMatch)})
					tNodeVersion.text=str(tVersion)



	def filter_init_all(self):
		for tNodeTarget in self.tXml.findall('Project/Server/Target'):
			tNodeTarget.set('filter', True)



	def filter_init_changed(self):
		tVersionSnapshot = deploy_version.version(0, 0, 0)
		for tNodeTarget in self.tXml.findall('Project/Server/Target'):
			bSelected = True
			# Loop over all versions.
			for tNodeVersion in tNodeTarget.findall('version'):
				tVersion = deploy_version.version(tNodeVersion.text)
				bMatch = self.to_bool(tNodeVersion.get('match'))
				if tVersion!=tVersionSnapshot and bMatch==True:
					bSelected = False
					break
			tNodeTarget.set('filter', bSelected)



	def artifacts_filter(self, strFilter):
		# Compile the regular expression.
		tRegEx = re.compile(strFilter)

		# Loop over all artifacts.
		for tNodeTarget in self.tXml.findall('Project/Server/Target'):
			# Only consider selected items.
			if tNodeTarget.get('filter')==True:
				tArtifact = self.read_target_node(tNodeTarget)

				# Combine the group and artifact ID into one string.
				strName = '%s.%s' % (tArtifact['gid'], tArtifact['aid'])
				tMatch = tRegEx.search(strName)
				if tMatch==None:
					tNodeTarget.set('filter', False)



	def artifacts_filter_apply(self, strVersion):
		# Loop over all artifacts.
		for tNodeTarget in self.tXml.findall('Project/Server/Target'):
			# Only consider selected items.
			if tNodeTarget.get('filter')==True:
				tArtifact = self.read_target_node(tNodeTarget)

				# This artifact will be deployed.
				tNodeTarget.set('selected', str(True))

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

				tNodeTarget.set('deploy_as', str(tDeployVersion))

				# Processed.
				tNodeTarget.set('filter', False)



	def execute_report(self):
		# Loop over all artifacts.
		for tNodeServer in self.tXml.findall('Project/Server'):
			# Get the server ID for all nodes.
			print 'Server %s:' % tNodeServer.get('id')

			# Loop over all targets for this server.
			for tNodeTarget in tNodeServer.findall('Target'):
				tArtifact = self.read_target_node(tNodeTarget)
				# Only consider selected items.
				if tArtifact['selected']==True:
					print '%s.%s : %s' % (tArtifact['gid'], tArtifact['aid'], str(tArtifact['deploy_as']))



	def execute_deploy(self):
		for tNodeServer in self.tXml.findall('Project/Server'):
			# Get the server ID for all nodes.
			strServerID = tNodeServer.get('id')
			strRepositoryRelease = tNodeServer.get('release')
			strRepositorySnapshots = tNodeServer.get('snapshots')

			# Set the credentials for this server.
			self.set_credentials(strServerID)

			# Loop over all targets for this server.
			for tNodeTarget in tNodeServer.findall('Target'):
				tArtifact = self.read_target_node(tNodeTarget)
				# Only consider selected items.
				if tArtifact['selected']==True:
					self.tRepositoryDriver.deploy(tArtifact, strRepositoryRelease, strRepositorySnapshots)



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

	# Read the credentials in the users home folder.
	tDeploy.read_credentials('~/.mbs_credentials.xml')
	# Add local credentials.
	tDeploy.read_credentials('.mbs_credentials.xml')

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

