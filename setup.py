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


iMinimumInterpreterVersion_maj = 2
iMinimumInterpreterVersion_min = 6

import sys
iMinimumInterpreterVersion_hex = (iMinimumInterpreterVersion_maj<<24) | (iMinimumInterpreterVersion_min<<16)
if sys.hexversion<iMinimumInterpreterVersion_hex:
	sys.exit('The setup script needs at least python %d.%d to run. Please update!'%(iMinimumInterpreterVersion_maj, iMinimumInterpreterVersion_min))

import hashlib
import os
import platform
import re
import runpy
import shutil
import subprocess
import tarfile
import urllib2
import urlparse

from string import Template
from xml.etree.ElementTree import ElementTree


def get_tool_path(aCfg, aTool):
	return os.path.join(aCfg['depack_path'], aTool['group'], aTool['name'], '%s-%s'%(aTool['name'],aTool['version']))


#
# Download the URL 'strUrl' to the file 'strFile'.
#
# Returns 'True' on success, 'False' on error.
#
def download_file(strUrl, strFile):
	bResult = False
	fOutput = None
	sizDownloaded = 0
	
	try:
		aSocket = urllib2.urlopen(strUrl)
		aInfo = aSocket.info()
		try:
			sizTotal = long(aInfo['content-length'])
		except KeyError:
			sizTotal = 0
		
		fOutput = open(strFile, 'wb')
		while 1:
			strChunk = aSocket.read(2048)
			sizChunk = len(strChunk)
			if sizChunk==0:
				break
			fOutput.write(strChunk)
			sizDownloaded += sizChunk
			if sizTotal!=0:
				print '%d%% (%d/%d)' % (100.0*sizDownloaded/sizTotal, sizDownloaded, sizTotal)
			else:
				print '%d' % sizDownloaded
		
		bResult = True
	except urllib2.HTTPError, e: 
		print 'Failed to download %s: %d' % (strUrl,e.code)
	
	if fOutput:
		fOutput.close()
	
	return bResult


#
# Check the Sha1 sum for a file.
# First extract the precalculated sha1 sum from the textfile 'strSha1File'.
# Then build our own sha1 sum of file 'strBinFile' and compare it with the sum
# from the textfile.
#
# Returns 'True' on success and 'False' on error.
#
def check_sha1_sum(strSha1File, strBinFile):
	bResult = False
	strRemoteHash = None
	
	tRegObj = re.compile('([0-9a-fA-F]+)')
	fInput = open(strSha1File, 'rt')
	for strLine in fInput:
		tMatchObj = tRegObj.match(strLine)
		if tMatchObj:
			# Get the hash.
			strRemoteHash = tMatchObj.group(1)
			break
	fInput.close()
	
	
	if strRemoteHash:
		tHashObj = hashlib.sha1()
	
		fInput = open(strBinFile, 'rb')
		while 1:
			strChunk = fInput.read(8192)
			if len(strChunk)==0:
				break
			tHashObj.update(strChunk)
		fInput.close()
	
		strLocalHash = tHashObj.hexdigest()
		if strRemoteHash==strLocalHash:
			bResult = True
	
	return bResult


def install_package(aCfg, aTool):
	print 'Processing package %s, version %s' % (aTool['name'], aTool['version'])
	
	# Construct the path for the depack marker.
	strLocalMarkerFolder = aCfg['marker_path']
	
	# Construct the path to the repository folder.
	strLocalRepositoryPath = aCfg['repository_path']
	
	# Construct the path to the depack folder.
	strPacketDepackPath = os.path.join(aCfg['depack_path'], aTool['group'], aTool['name'])
	
	# Construct the package name.
	strPackageName = '%s-%s.%s'%(aTool['package'],aTool['version'],aTool['typ'])
	strSha1Name = strPackageName + '.sha1'
	
	aPathElements = aTool['group'].split('.')
	aPathElements.append(aTool['package'])
	aPathElements.append(aTool['version'])
	
	strLocalMarkerPath = os.path.join(strLocalMarkerFolder, '%s-%s-%s-%s.marker'%(aTool['group'],aTool['name'],aTool['typ'],aTool['version']))
	
	# Construct the path in the repository.
	strLocalPackageFolder = os.path.join(strLocalRepositoryPath, *aPathElements)
	strLocalPackagePath = os.path.join(strLocalPackageFolder, strPackageName)
	strLocalSha1Path = strLocalPackagePath + '.sha1'
	
	# Create the directories.
	if os.path.isdir(strLocalMarkerFolder)==False:
		os.makedirs(strLocalMarkerFolder)
	
	if os.path.isdir(strLocalRepositoryPath)==False:
		os.makedirs(strLocalRepositoryPath)
	
	if os.path.isdir(strLocalPackageFolder)==False:
		os.makedirs(strLocalPackageFolder)
	
	if os.path.isdir(strPacketDepackPath)==False:
		os.makedirs(strPacketDepackPath)
	
	if os.path.isfile(strLocalMarkerPath)==True:
		print 'The package is already installed.'
	else:
		print 'The package is not installed yet.'
		
		# Both the package and the sha1 must exist.
		bDownloadOk = os.path.isfile(strLocalPackagePath) and os.path.isfile(strLocalSha1Path)
		
		if bDownloadOk==True:
			print 'The package was already downloaded, check the files.'
			# Check the sha1 sum.
			bDownloadOk = check_sha1_sum(strLocalSha1Path, strLocalPackagePath)
			if bDownloadOk==True:
				print 'The checksums match: OK!'
			else:
				print 'Checksum mismatch, discarding downloaded files!'
				os.remove(strLocalPackagePath)
				os.remove(strLocalSha1Path)
		
		if bDownloadOk==False:
			print 'The package must be downloaded.'
			
			for strRepositoryUrl in aCfg['repositories']:
				if strRepositoryUrl[-1]!='/':
					strRepositoryUrl += '/'
				print 'Trying repository at %s...' % strRepositoryUrl
				strPackageUrl = strRepositoryUrl + '/'.join(aPathElements) + '/' + strPackageName
				strSha1Url = strPackageUrl + '.sha1'
				
				bDownloadOk = download_file(strSha1Url, strLocalSha1Path)
				if bDownloadOk==True:
					bDownloadOk = download_file(strPackageUrl, strLocalPackagePath)
					if bDownloadOk==True:
						# Check the sha1 sum.
						bDownloadOk = check_sha1_sum(strLocalSha1Path, strLocalPackagePath)
						if bDownloadOk==True:
							print 'The checksums match: OK!'
							break
						else:
							print 'Checksum mismatch, discarding downloaded files!'
							os.remove(strLocalPackagePath)
							os.remove(strLocalSha1Path)
			
			if bDownloadOk==False:
				raise Exception('Failed to download the package %s!'%strPackageName)
		
		if bDownloadOk==True:
			# Unpack the archive.
			print 'Unpacking...'
			tArchive = tarfile.open(strLocalPackagePath)
			tArchive.extractall(strPacketDepackPath)
			tArchive.close()
			
			# Create the depack marker.
			fMarker = open(strLocalMarkerPath, 'w')
			fMarker.close()


def create_substitute_dict(aCfg):
	# Get the scons path.
	strSconsPath = aCfg['scons_path']
	
	# Get the project version.
	strProjectVersion = '%d.%d' % (aCfg['project_version_maj'], aCfg['project_version_min'])
	
	# Get the tools.
	aToolPaths = []
	for aTool in aCfg['tools']:
		strToolPath = os.path.join(aCfg['depack_path'], aTool['group'], aTool['name']).replace('\\', '/')
		aToolPaths.append('\'%s-%s\': \'%s\'' % (aTool['name'],aTool['version'], strToolPath))
	
	strTools  = 'dict({' + ','.join(aToolPaths) + '})'
	
	# apply the project version to the environment
	aSubstitute = dict({
		'NOTE': 'NOTE: This file was generated by setup.py . Any changes will be lost!',
		'PYTHON': sys.executable,
		'SCONS_DIR': strSconsPath,
		'PROJECT_VERSION': strProjectVersion,
		'TOOLS': strTools,
		'MBS_DIR' : strMbsDir
	})
	return aSubstitute


def filter_file(aSubstitute, strDstPath, strSrcPath):
	print 'Filter %s -> %s' % (strSrcPath, strDstPath)
	
	# Read the template.
	src_file = open(strSrcPath, 'r')
	src_txt = src_file.read()
	src_file.close()
	tTemplate = Template(src_txt)
	dst_newtxt = tTemplate.safe_substitute(aSubstitute)
	
	# Read the destination (if exists).
	try:
		dst_file = open(strDstPath, 'r')
		dst_oldtxt = dst_file.read()
		dst_file.close()
	except IOError:
		dst_oldtxt = ''
	
	if dst_newtxt!=dst_oldtxt:
		# overwrite the file
		dst_file = open(strDstPath, 'w')
		dst_file.write(dst_newtxt)
		dst_file.close()
		# Copy the permission bits.
		shutil.copymode(strSrcPath, strDstPath)


def read_tool(tNode):
	aBaseMachine = dict({
		'i486': 'i386',
		'i586': 'i386',
		'i686': 'i386'
	})
	
	strGroup = tNode.findtext('group')
	strName = tNode.findtext('name')
	strPackage = tNode.findtext('package')
	strVersion = tNode.findtext('version')
	strTyp = tNode.findtext('typ')
	
	strMachineName = platform.machine()
	if strMachineName in aBaseMachine:
		strMachineName = aBaseMachine[strMachineName]
	
	aToolSubstutite = dict({
		'platform': platform.system().lower(),
		'machine': strMachineName
	})
	
	tTemplate = Template(strPackage)
	
	return dict({
		'group': strGroup,
		'name': strName,
		'package': tTemplate.safe_substitute(aToolSubstutite),
		'version': strVersion,
		'typ': strTyp
	})


def read_config_paths(aCfg, tXml):
	strPath = tXml.findtext('paths/marker')
	if strPath!=None:
		aCfg['marker_path'] = os.path.abspath(os.path.expanduser(strPath))
	
	strPath = tXml.findtext('paths/repository')
	if strPath!=None:
		aCfg['repository_path'] = os.path.abspath(os.path.expanduser(strPath))
	
	strPath = tXml.findtext('paths/depack')
	if strPath!=None:
		aCfg['depack_path'] = os.path.abspath(os.path.expanduser(strPath))


def read_user_config(strConfigPath, aCfg):
	strRealPath = os.path.abspath(os.path.expanduser(strConfigPath))
	if os.path.isfile(strRealPath)==True:
		tXml = ElementTree()
		tXml.parse(strRealPath)
		
		read_config_paths(aCfg, tXml)
		
		iInsertPos = 0
		for tNode in tXml.findall('repositories/repository'):
			# Insert the user repositories before the default entries.
			aCfg['repositories'].insert(iInsertPos, tNode.text)
			iInsertPos += 1


def read_project_config(strConfigPath, aCfg):
	if os.path.isfile(strConfigPath)==True:
		tXml = ElementTree()
		tXml.parse(strConfigPath)
		
		aCfg['project_version_maj'] = long(tXml.findtext('project_version/major'))
		aCfg['project_version_min'] = long(tXml.findtext('project_version/minor'))
		
		strPath = tXml.findtext('paths/marker')
		if strPath!=None:
			aCfg['marker_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		strPath = tXml.findtext('paths/repository')
		if strPath!=None:
			aCfg['repository_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		strPath = tXml.findtext('paths/depack')
		if strPath!=None:
			aCfg['depack_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		tElement = tXml.find('repositories')
		if tElement!=None:
			# Replace all other elements?
			strReplace = tElement.get('replace')
			if strReplace in ['true', 'True', 'yes', 'Yes']:
				aCfg['repositories'] = dict({})
			# Insert the projects repositories before all other entries.
			iInsertPos = 0
			for tNode in tXml.findall('repositories/repository'):
				aCfg['repositories'].insert(iInsertPos, tNode.text)
				iInsertPos += 1
		
		aCfg['scons'] = read_tool(tXml.find('scons'))
		
		aTools = []
		for tNode in tXml.findall('tools/tool'):
			aTools.append(read_tool(tNode))
		aCfg['tools'] = aTools
	
		tElement = tXml.find('filters')
		if tElement!=None:
			strReplace = tElement.get('replace')
			if strReplace in ['true', 'True', 'yes', 'Yes']:
				aCfg['filter'] = dict({})
			
			for tNode in tXml.findall('filters/filter'):
				strTemplate = tNode.findtext('template')
				strDst = tNode.findtext('destination')
				if strTemplate!=None and strDst!=None:
					aCfg['filter'][strDst] = strTemplate
	return aCfg


# Get the relative path from the current folder to the muhkuh build system.
strMbsDir = os.path.relpath(os.path.dirname(os.path.realpath(__file__)))

# Set the defaults.
aCfg = dict({
	'marker_path': os.path.abspath(os.path.expanduser('~/.mbs/depack')),
	'repository_path': os.path.abspath(os.path.expanduser('~/.mbs/repository')),
	'depack_path': os.path.abspath(os.path.expanduser('~/.mbs/depack')),
	'repositories': ['http://downloads.sourceforge.net/project/muhkuh/mbs'],
	'filter': dict({
		'scons.bat': 'templates/scons.bat',
		'scons.sh': 'templates/scons.sh',
		'site_scons/site_init.py': 'templates/site_init.py'
	})
})
read_user_config('~/.mbs.xml', aCfg)
read_project_config('setup.xml', aCfg)

# Install Scons.
install_package(aCfg, aCfg['scons'])
aToolScons = aCfg['scons']
aCfg['scons_path'] = os.path.join(get_tool_path(aCfg, aToolScons), 'scons.py')


# Install all other tools.
for aTool in aCfg['tools']:
	install_package(aCfg, aTool)


# Filter the files.
aSubstitute = create_substitute_dict(aCfg)
for strDst,strSrc in aCfg['filter'].items():
	# Get the source file from the project folder.
	strPrjSrc = os.path.join(strMbsDir, strSrc)
	# Create the destination folder.
	strDstFolder = os.path.dirname(strDst)
	if strDstFolder!='' and os.path.exists(strDstFolder)==False:
		os.makedirs(strDstFolder)
	filter_file(aSubstitute, strDst, strPrjSrc)


# Run Scons (use aCfg['scons'] to get the path. All archives *must* create a folder with the name
# '%s-%s'%(strName,strVersion) and have a 'scons.py' there.
print 'Running scons (%s)' % aCfg['scons_path']
subprocess.call([sys.executable, aCfg['scons_path']])
