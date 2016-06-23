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

import hashlib
import os
import os.path
import platform
import re
import string
import tarfile

import download

#
# Check the Sha1 sum for a file.
# First extract the SHA1 sum from the text file 'strSha1File'.
# Then build our own SHA1 sum of file 'strBinFile' and compare it with the sum
# from the text file.
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



def getToolAttributes(aCfg, aTool, strPackageMachine):
	aAttr = dict({})

	# Construct the path for the marker.
	aAttr['LocalMarkerFolder'] = aCfg['marker_path']
	
	# Construct the path to the repository folder.
	aAttr['LocalRepositoryPath'] = aCfg['repository_path']
	
	# Construct the path to the depack folder.
	aAttr['PacketDepackPath'] = os.path.join(aCfg['depack_path'], aTool['group'], aTool['name'])
	
	# Construct the package name.
	strPackageName = '%s-%s.%s'%(strPackageMachine,aTool['version'],aTool['typ'])
	aAttr['PackageName'] = strPackageName
	aAttr['Sha1Name'] = strPackageName + '.sha1'
	
	aPathElements = aTool['group'].split('.')
	aPathElements.append(strPackageMachine)
	aPathElements.append(aTool['version'])
	aAttr['PathElements'] = aPathElements
	
	aAttr['LocalMarkerPath'] = os.path.join(aCfg['marker_path'], '%s-%s-%s-%s.marker'%(aTool['group'],aTool['name'],aTool['typ'],aTool['version']))
	
	# Construct the path in the repository.
	aAttr['LocalPackageFolder'] = os.path.join(aCfg['repository_path'], *aPathElements)
	aAttr['LocalPackagePath'] = os.path.join(aAttr['LocalPackageFolder'], strPackageName)
	aAttr['LocalSha1Path'] = aAttr['LocalPackagePath'] + '.sha1'

	return aAttr



def install_package(aCfg, aToolAttr):
	if os.path.isdir(aToolAttr['LocalPackageFolder'])==False:
		os.makedirs(aToolAttr['LocalPackageFolder'])

	if os.path.isdir(aToolAttr['PacketDepackPath'])==False:
		os.makedirs(aToolAttr['PacketDepackPath'])

	# Is the package already downloaded?
	# Both the package and the sha1 must exist.
	bDownloadOk = os.path.isfile(aToolAttr['LocalPackagePath']) and os.path.isfile(aToolAttr['LocalSha1Path'])
	
	if bDownloadOk==True:
		print 'The package was already downloaded, check the files.'
		# Check the sha1 sum.
		bDownloadOk = check_sha1_sum(aToolAttr['LocalSha1Path'], aToolAttr['LocalPackagePath'])
		if bDownloadOk==True:
			print 'The checksums match: OK!'
		else:
			print 'Checksum mismatch, discarding downloaded files!'
			os.remove(aToolAttr['LocalPackagePath'])
			os.remove(aToolAttr['LocalSha1Path'])
		
	if bDownloadOk==False:
		print 'The package is not in the repository. It must be downloaded.'
			
		for strRepositoryUrl in aCfg['repositories']:
			if strRepositoryUrl[-1]!='/':
				strRepositoryUrl += '/'
			print 'Trying repository at %s...' % strRepositoryUrl
			strPackageUrl = strRepositoryUrl + '/'.join(aToolAttr['PathElements']) + '/' + aToolAttr['PackageName']
			strSha1Url = strPackageUrl + '.sha1'
				
			bDownloadOk = download.download_to_file(strSha1Url, aToolAttr['LocalSha1Path'])
			if bDownloadOk==True:
				bDownloadOk = download.download_to_file(strPackageUrl, aToolAttr['LocalPackagePath'])
				if bDownloadOk==True:
					# Check the sha1 sum.
					bDownloadOk = check_sha1_sum(aToolAttr['LocalSha1Path'], aToolAttr['LocalPackagePath'])
					if bDownloadOk==True:
						print 'The checksums match: OK!'
						break
					else:
						print 'Checksum mismatch, discarding downloaded files!'
						os.remove(aToolAttr['LocalPackagePath'])
						os.remove(aToolAttr['LocalSha1Path'])
		
	if bDownloadOk==True:
		# Unpack the archive.
		print 'Unpacking...'
		tArchive = tarfile.open(aToolAttr['LocalPackagePath'])
		tArchive.extractall(aToolAttr['PacketDepackPath'])
		tArchive.close()
			
		# Create the depack marker.
		fMarker = open(aToolAttr['LocalMarkerPath'], 'w')
		fMarker.close()

	return bDownloadOk



atMachineFallbacks = dict({
	# Linux 32 bit.
	'i486': ['i486', 'i386'],
	'i586': ['i586', 'i486', 'i386'],
	'i686': ['i686', 'i586', 'i486', 'i386'],
	'x86_64': ['x86_64', 'i686', 'i586', 'i486', 'i386'],

	# Windows 64 bit.
	'amd64': ['amd64', 'x86']
})

def process_package(aCfg, aTool):
	print 'Processing package %s, version %s' % (aTool['name'], aTool['version'])

	# Nothing found yet.
	aToolAttr = None
	
	# Does the package have a machine placeholder?
	strPackage = aTool['package']
	if string.find(strPackage, '${machine}') > -1:
		# Get the machine name and possible alternatives.
		strMachineName = platform.machine().lower()
		if strMachineName in atMachineFallbacks:
			astrMachines = atMachineFallbacks[strMachineName]
		else:
			astrMachines = [strMachineName]
	
		tTemplate = string.Template(strPackage)

		# Loop over all possible machine types.
		for strMachineName in astrMachines:
			# Substitute the machine name in the package name.
			strPackageMachine = tTemplate.safe_substitute(dict({ 'machine': strMachineName }))
			print 'Looking for installed package %s.' % strPackageMachine
			
			# Get all attributes for the tool.
			aToolAttr = getToolAttributes(aCfg, aTool, strPackageMachine)

			# Check if this package name is installed.
			if os.path.isfile(aToolAttr['LocalMarkerPath'])==True:
				# Use this package.
				print 'Found package!'
				break
			else:
				aToolAttr = None
		
		if aToolAttr is None:
			# Loop over all possible machine types.
			for strMachineName in astrMachines:
				# Substitute the machine name in the package name.
				strPackageMachine = tTemplate.safe_substitute(dict({ 'machine': strMachineName }))
				print 'Trying to install package %s.' % strPackageMachine
			
				# Get all attributes for the tool.
				aToolAttr = getToolAttributes(aCfg, aTool, strPackageMachine)

				# Install package.
				fResult = install_package(aCfg, aToolAttr)
				if fResult==True:
					print 'Installed package.'
					break
				else:
					aToolAttr = None
		
	else:
		# Get all attributes for the tool.
		aToolAttr = getToolAttributes(aCfg, aTool, strPackage)

		# Check if this package name is installed.
		if os.path.isfile(aToolAttr['LocalMarkerPath'])==True:
			# Use this package.
			print 'Found package!'
		else:
			fResult = install_package(aCfg, aToolAttr)
			if fResult==True:
				print 'Installed package.'
			else:
				aToolAttr = None

	if aToolAttr is None:
		raise Exception('Failed to install package %s, version %s' % (aTool['name'], aTool['version']))
	
	return aToolAttr


