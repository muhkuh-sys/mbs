# -*- coding: utf-8 -*-


import httplib2


class RestDriver:
	def __init__(self):
		self.tClient = httplib2.Http('.cache')


	def set_credentials(self, strUser, strPasswd):
		self.tClient.add_credentials(strUser, strPasswd)


	def get(self, strHost, strUrl):
		tResponse, aucContent = self.tClient.request("http://" + strHost + "/" + strUrl)
		if tResponse.status!=200:
			raise Exception('Http Error: %d' % tResponse.status)
		return aucContent


	def put_string(self, strHost, strUrl, strData):
		tResponse, aucContent = self.tClient.request("http://" + strHost + "/" + strUrl, 'PUT', body=strData, headers={'content-type':'text/plain'} )
		print tResponse
		print aucContent


	def put_file(self, strUrl, strFileName):
		tFile = open(strFileName, 'rb')
		strFileData = tFile.read()
		tFile.close()

		resp, content = self.tClient.request("http://" + strHost + "/" + strUrl, 'PUT', body=strFileData, headers={'content-type':'text/plain'} )



