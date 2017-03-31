# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2016 by Christoph Thelen                                #
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
import os.path
import string

import SCons
import SCons.Node.FS
from SCons.Script import *


def hash_action(target, source, env):
	# Init the results array.
	aHashes = []

	tTemplate = string.Template(env['HASH_TEMPLATE'])

	# Get the directory path of the target file. This is the working dir and all paths in the hash file must be relative to this.
	strWorkingDir = os.path.dirname(target[0].get_path())

	# Create a new hash object with the requested algorithm.
	astrHashIDs = string.split(env['HASH_ALGORITHM'], ',')
	for strHashName in astrHashIDs:
		strHashID = string.lower(string.strip(strHashName))
		strHashID_upper = string.upper(strHashID)

		try:
			tHashBase = hashlib.new(strHashID)
		except ValueError:
			raise Exception('Unknown hash algorithm "%s". Supported algorithms: %s' % (strHashID, ', '.join(hashlib.algorithms)))

		# Loop over all sources.
		for tSource in source:
			# Get a copy of the hash base.
			tHash = tHashBase.copy()
			# Process the complete file.
			tHash.update(tSource.get_contents())
			# Get the relative path to the working folder.
			strRelPath = os.path.relpath(tSource.get_path(), strWorkingDir)
			# Append the hash sum to the results.
			aSubstitute = dict({
				'ID': strHashID,
				'ID_UC': strHashID_upper,
				'HASH': tHash.hexdigest(),
				'PATH': strRelPath
			})
			aHashes.append(tTemplate.safe_substitute(aSubstitute))

	# Write all hashes to the target file.
	tFileTarget = open(target[0].get_path(), 'w')
	tFileTarget.writelines(aHashes)
	tFileTarget.close()

	return 0


def hash_emitter(target, source, env):
	# Make the target depend on the parameter.
	Depends(target, SCons.Node.Python.Value(env['HASH_ALGORITHM']))
	Depends(target, SCons.Node.Python.Value(env['HASH_TEMPLATE']))

	return target, source


def hash_string(target, source, env):
	return 'Hash %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add Hash builder.
	#
	env['HASH_ALGORITHM'] = 'sha1'
	env['HASH_TEMPLATE'] = '${HASH} *${PATH}\n'


	hash_act = SCons.Action.Action(hash_action, hash_string)
	hash_bld = Builder(action=hash_act, emitter=hash_emitter)
	env['BUILDERS']['Hash'] = hash_bld

