# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
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
# ----------------------------------------------------------------------- #

import SCons
import SCons.Node.FS


def concat_action(target, source, env):
    # Write all output to the target file.
    tFileTarget = open(target[0].get_path(), 'wb')

    # Loop over all sources.
    for tSource in source:
        # Copy the file in chunks.
        tFileSrc = open(tSource.get_path(), 'rb')
        while True:
            tChunk = tFileSrc.read(16384)
            if (tChunk is None) or (len(tChunk) == 0):
                break
            tFileTarget.write(tChunk)
        tFileSrc.close()
    tFileTarget.close()

    return 0


def concat_emitter(target, source, env):
    return target, source


def concat_string(target, source, env):
    return 'Concat %s' % target[0].get_path()


def ApplyToEnv(env):
    # -------------------------------------------------------------------------
    #
    # Add Concat builder.
    #
    concat_act = SCons.Action.Action(concat_action, concat_string)
    concat_bld = SCons.Builder.Builder(action=concat_act, emitter=concat_emitter)
    env['BUILDERS']['Concat'] = concat_bld
