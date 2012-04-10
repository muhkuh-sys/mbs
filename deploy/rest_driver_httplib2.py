# -*- coding: utf-8 -*-


import httplib2


class RestDriver:
	def __init__(self):
		self.tClient = httplib2.Http('.cache')


	def set_credentials(self, strUser, strPasswd):
		self.tClient.add_credentials(strUser, strPasswd)

	def get(self, tUrl, strPath):
		strUrl = '%s://%s/%s%s' % (tUrl.scheme, tUrl.netloc, tUrl.path, strPath)
		tResponse, aucContent = self.tClient.request(strUrl)
		if tResponse.status!=200:
			raise Exception('Http Error: %d' % tResponse.status)
		return aucContent


	def put_string(self, tUrl, strPath, strData):
		strUrl = '%s://%s/%s%s' % (tUrl.scheme, tUrl.netloc, tUrl.path, strPath)
		tResponse, aucContent = self.tClient.request(strUrl, 'PUT', body=strData, headers={'content-type':'text/plain'} )
		if tResponse.status!=201:
			raise Exception('Http Error: %d' % tResponse.status)


	def put_file(self, tUrl, strPath, strFileName):
		strUrl = '%s://%s/%s%s' % (tUrl.scheme, tUrl.netloc, tUrl.path, strPath)

		tFile = open(strFileName, 'rb')
		strFileData = tFile.read()
		tFile.close()

		tResponse, aucContent = self.tClient.request(strUrl, 'PUT', body=strFileData, headers={'content-type':'text/plain'} )
		if tResponse.status!=201:
			raise Exception('Http Error: %d' % tResponse.status)



