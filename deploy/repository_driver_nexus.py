# -*- coding: utf-8 -*-


import hashlib
import deploy_version

from string import Template
from urlparse import urlparse
from xml.etree.ElementTree import XML


# The repository class capsules access to the artifact repository.
class RepositoryDriver:
	strPomTemplate = '''<project xmlns="http://maven.apache.org/POM/4.0.0"
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

	strUrlLuceneSearchGA   = 'service/local/lucene/search?g=%s&a=%s'

	strUrlLuceneSearchSha1 = 'service/local/lucene/search?sha1=%s'



	def __init__(self, tRestDriver, strHost):
		self.tRestDriver = tRestDriver
		self.strHost = strHost

		# Create the base object for the hash sums.
		self.tHashSha1Base = hashlib.new('sha1')



	def set_credentials(self, aCredentials):
		self.tServerBaseUrl = urlparse(aCredentials['url'])

		# Pass the user and password to the rest driver.
		self.tRestDriver.set_credentials(aCredentials['user'], aCredentials['password'])



	def generate_pom(self, strGroupID, strArtifactID, strPackaging, strVersion):
		aSubstitute = dict({
			'GROUP_ID': strGroupID,
			'ARTIFACT_ID' : strArtifactID,
			'VERSION' : strVersion,
			'PACKAGING' : strPackaging
		})
	
		tTemplate = Template(self.strPomTemplate)
		return tTemplate.safe_substitute(aSubstitute)



	def generate_sha1_from_file(self, strFileName):
		# Generate the SHA1 sum for the file.
		tHash = self.tHashSha1Base.copy()
		tFile = open(strFileName, 'rb')
		while True:
			strChunk = tFile.read(8192)
			tHash.update(strChunk)
			if len(strChunk):
				break
		tFile.close()
		return tHash.hexdigest()



	def generate_sha1_from_string(self, strData):
		# Generate the SHA1 sum for the string.
		tHash = self.tHashSha1Base.copy()
		tHash.update(strData)
		return tHash.hexdigest()



	def getAllArtifactVersions(self, strGroupID, strArtifactID):
		atVersions = []

		strPath = self.strUrlLuceneSearchGA % (strGroupID, strArtifactID)
		aucContent = self.tRestDriver.get(self.tServerBaseUrl, strPath)
		tSearchResult = XML(aucContent)

		# The search result must be complete.
		if tSearchResult.findtext('tooManyResults')!='false':
			raise Exception("Received a truncated search result!")
	
		# Loop over all results.
		for tNode in tSearchResult.findall('data/artifact'):
			strVersion = tNode.findtext('version')
			if isinstance(strVersion, basestring)==True:
				strVersion = strVersion.strip()
				if strVersion=='SNAPSHOT':
					tVersion = deploy_version.version(0, 0, 0)
				else:
					tVersion = deploy_version.version(strVersion)
				atVersions.append(tVersion)

		# Sort the versions.
		atVersions.sort()

		return atVersions


	def findSha1Artifacts(self, strFileName, strGroupID, strArtifactID):
		atVersions = []

		# Generate the SHA1 sum for the file.
		strFileSha1 = self.generate_sha1_from_file(strFileName)

		strPath = self.strUrlLuceneSearchSha1 % strFileSha1
		aucContent = self.tRestDriver.get(self.tServerBaseUrl, strPath)
		tSearchResult = XML(aucContent)

		# The search result must be complete.
		if tSearchResult.findtext('tooManyResults')!='false':
			raise Exception("Received a truncated search result!")
	
		# Loop over all results.
		for tNode in tSearchResult.findall('data/artifact'):
			strG = tNode.findtext('groupId')
			strA = tNode.findtext('artifactId')
			strVersion = tNode.findtext('version')

			if isinstance(strG, basestring)==True and isinstance(strA, basestring)==True and isinstance(strVersion, basestring)==True:
				strG = strG.strip()
				strA = strA.strip()
				strVersion = strVersion.strip()
				if strGroupID==strG and strArtifactID==strA:
					if strVersion=='SNAPSHOT':
						tVersion = deploy_version.version(0, 0, 0)
					else:
						tVersion = deploy_version.version(strVersion)
					atVersions.append(tVersion)

		atVersions.sort()

		return atVersions



	def deploy(self, tArtifact, strRepositoryRelease, strRepositorySnapshot):
		# Is this a snapshot release?
		bIsSnapshot = (tArtifact['deploy_as']==deploy_version.version(0, 0, 0))

		# Get the version string.
		strGID = tArtifact['gid']
		strAID = tArtifact['aid']
		strPackaging = tArtifact['packaging']
		strVersion = str(tArtifact['deploy_as'])

		astrDeployPath = []
		# Add the path to the repositories.
		# NOTE: This is fixed for nexus.
		astrDeployPath = ['content', 'repositories']

		# Append the repository name.
		if bIsSnapshot==True:
			astrDeployPath.append(strRepositorySnapshot)
		else:
			astrDeployPath.append(strRepositoryRelease)

		# Generate the artifact specific part of the path.
		astrDeployPath.extend(strGID.split('.'))
		astrDeployPath.append(strAID)
		astrDeployPath.append(strVersion)

		strLocalPath_Artifact = tArtifact['file']

		strRemotePath_Base = '%s/%s-%s.' % ('/'.join(astrDeployPath), strAID, strVersion)

		strRemotePath_Artifact     = strRemotePath_Base     + strPackaging
		strRemotePath_ArtifactHash = strRemotePath_Artifact + '.sha1'
		strRemotePath_Pom          = strRemotePath_Base     + 'pom'
		strRemotePath_PomHash      = strRemotePath_Pom      + '.sha1'

		print '%s:' % strLocalPath_Artifact
		print '\t%s' % strRemotePath_Artifact
		print '\t%s' % strRemotePath_Pom

		strFileHash = self.generate_sha1_from_file(strLocalPath_Artifact)
		strPom = self.generate_pom(strGID, strAID, strPackaging, strPackaging)
		strPomHash = self.generate_sha1_from_string(strPom)

		# Upload the hash sum of the artifact.
		self.tRestDriver.put_string(self.tServerBaseUrl, strRemotePath_ArtifactHash, strFileHash)

		# Upload the artifact.
		self.tRestDriver.put_file(self.tServerBaseUrl, strRemotePath_Artifact, strLocalPath_Artifact)

		# Upload the hash sum of the POM.
		self.tRestDriver.put_string(self.tServerBaseUrl, strRemotePath_PomHash, strPomHash)

		# Upload the POM.
		self.tRestDriver.put_string(self.tServerBaseUrl, strRemotePath_Pom, strPom)


