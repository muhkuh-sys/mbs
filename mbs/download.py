import urllib2

import progress

#
# Download the URL 'strUrl' to the file 'strFile'.
#
# Returns 'True' on success, 'False' on error.
#
def download_to_file(strUrl, strFile):
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
		tProgress = progress.ProgressOutput(sizTotal)
		
		fOutput = open(strFile, 'wb')
		while 1:
			strChunk = aSocket.read(2048)
			sizChunk = len(strChunk)
			if sizChunk==0:
				break
			fOutput.write(strChunk)
			sizDownloaded += sizChunk
			tProgress.update(sizChunk)

		tProgress.finish()
		bResult = True
	except urllib2.HTTPError, e: 
		print 'Failed to download %s: %d' % (strUrl,e.code)
	
	if fOutput:
		fOutput.close()
	
	return bResult
