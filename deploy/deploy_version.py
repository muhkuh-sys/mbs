# -*- coding: utf-8 -*-


import re

# The version class accepts a version number either as string or three numbers.
# A version object can be compared to another version. Addition and subtraction are
# also possible. Furthermore the version components can be accessed with lVersion_Maj, *_Min and *_Sub.
class version():
	def __init__(self, *args):
		if len(args)==0:
			# Init the version number.
			self.lVersion_Maj = 0
			self.lVersion_Min = 0
			self.lVersion_Sub = 0
		elif len(args)==1 and isinstance(args[0], basestring):
			# Try to parse the version string.
			tMatch = re.match("(\d+).(\d+).(\d+)", args[0])
			if tMatch:
				self.lVersion_Maj = long(tMatch.group(1))
				self.lVersion_Min = long(tMatch.group(2))
				self.lVersion_Sub = long(tMatch.group(3))
		elif len(args)==3:
			# Try to convert each argument to a long.
			self.lVersion_Maj = long(args[0])
			self.lVersion_Min = long(args[1])
			self.lVersion_Sub = long(args[2])


	def __repr__(self):
		return '[%d, %d, %d]' % (self.lVersion_Maj, self.lVersion_Min, self.lVersion_Sub)


	def __str__(self):
		return '%d.%d.%d' % (self.lVersion_Maj, self.lVersion_Min, self.lVersion_Sub)


	def __lt__(tVer0, tVer1):
		# Check if the major version is larger ( 1.0.0>2.0.0 = False )
		if tVer0.lVersion_Maj>tVer1.lVersion_Maj:
			fIsLessThan = False
		elif tVer0.lVersion_Maj<tVer1.lVersion_Maj:
			fIsLessThan = True
		elif tVer0.lVersion_Min>tVer1.lVersion_Min:
			fIsLessThan = False
		elif tVer0.lVersion_Min<tVer1.lVersion_Min:
			fIsLessThan = True
		elif tVer0.lVersion_Sub>tVer1.lVersion_Sub:
			fIsLessThan = False
		elif tVer0.lVersion_Sub<tVer1.lVersion_Sub:
			fIsLessThan = True
		else:
			fIsLessThan = False
		return fIsLessThan


	def __le__(tVer0, tVer1):
		return version.__lt__(tVer0, tVer1) or version.__eq__(tVer0, tVer1)


	def __eq__(tVer0, tVer1):
		fIsEqual = (tVer0.lVersion_Maj==tVer1.lVersion_Maj) and (tVer0.lVersion_Min==tVer1.lVersion_Min) and (tVer0.lVersion_Sub==tVer1.lVersion_Sub)
		return fIsEqual


	def __ne__(tVer0, tVer1):
		return not(version.__eq__(tVer0, tVer1))


	def __ge__(tVer0, tVer1):
		return version.__le__(tVer1, tVer0)


	def __gt__(tVer0, tVer1):
		return version.__lt__(tVer1, tVer0)


	def __add__(tVer0, tVer1):
		lVersion_Maj = tVer0.lVersion_Maj + tVer1.lVersion_Maj
		lVersion_Min = tVer0.lVersion_Min + tVer1.lVersion_Min
		lVersion_Sub = tVer0.lVersion_Sub + tVer1.lVersion_Sub
		return version(lVersion_Maj, lVersion_Min, lVersion_Sub)


	def __sub__(tVer0, tVer1):
		lVersion_Maj = tVer0.lVersion_Maj - tVer1.lVersion_Maj
		lVersion_Min = tVer0.lVersion_Min - tVer1.lVersion_Min
		lVersion_Sub = tVer0.lVersion_Sub - tVer1.lVersion_Sub
		return version(lVersion_Maj, lVersion_Min, lVersion_Sub)


	def __iadd__(self, tVer1):
		self.lVersion_Maj = self.lVersion_Maj + tVer1.lVersion_Maj
		self.lVersion_Min = self.lVersion_Min + tVer1.lVersion_Min
		self.lVersion_Sub = self.lVersion_Sub + tVer1.lVersion_Sub
		return self


	def __isub__(self, tVer1):
		self.lVersion_Maj = self.lVersion_Maj - tVer1.lVersion_Maj
		self.lVersion_Min = self.lVersion_Min - tVer1.lVersion_Min
		self.lVersion_Sub = self.lVersion_Sub - tVer1.lVersion_Sub
		return self

