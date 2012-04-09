# -*- coding: utf-8 -*-


import hashlib
import deploy_version

from xml.etree.ElementTree import XML


# The repository class capsules access to the artifact repository.
class RepositoryDriver:
	def __init__(self, tRestDriver, strUrlServer):
		self.tRestDriver = tRestDriver
		self.strUrlServer = strUrlServer

		self.strUrlLuceneSearchGA   = 'service/local/lucene/search?g=%s&a=%s'
		self.strUrlLuceneSearchSha1 = 'service/local/lucene/search?sha1=%s'

		# Create the base object for the hash sums.
		self.tHashSha1Base = hashlib.new('sha1')


	def getAllArtifactVersions(self, strGroupID, strArtifactID):
		atVersions = []

		strUrl = self.strUrlServer + self.strUrlLuceneSearchGA % (strGroupID, strArtifactID)
		aucContent = self.tRestDriver.get(strUrl)
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
		tHash = self.tHashSha1Base.copy()
		tFile = open(strFileName, 'rb')
		while True:
			strSha1Chunk = tFile.read(8192)
			tHash.update(strSha1Chunk)
			if len(strSha1Chunk):
				break
		tFile.close()
		strFileSha1 = tHash.hexdigest()

		strUrl = self.strUrlServer + self.strUrlLuceneSearchSha1 % strFileSha1
		aucContent = self.tRestDriver.get(strUrl)
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

