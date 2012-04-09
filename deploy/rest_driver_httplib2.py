# -*- coding: utf-8 -*-


import httplib2


class RestDriver:
	def __init__(self):
		self.tClient = httplib2.Http('.cache')


	def get(self, strUrl):
		tResponse, aucContent = self.tClient.request(strUrl)
		if tResponse.status!=200:
			raise Exception('Http Error: %d' % tResponse.status)
		return aucContent


