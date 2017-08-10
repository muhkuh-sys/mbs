# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
#   Copyright (C) 2017 by Christoph Thelen                                #
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


import string
import SCons


def filter_action(target, source, env):
    if 'SUBSTITUTIONS' in env:
        atSubstitutions = dict(env['SUBSTITUTIONS'])
    else:
        atSubstitutions = {}

    # Read the template.
    tTemplate = string.Template(source[0].get_contents())

    # Read the destination (if exists).
    try:
        dst_oldtxt = target[0].get_contents()
    except IOError:
        dst_oldtxt = ''

    # Filter the src file.
    # NOTE: This replaces only $ID and ${ID}.
    dst_newtxt = tTemplate.safe_substitute(atSubstitutions)

    # Replace @ID@.
    for strKey, tValue in atSubstitutions.items():
        dst_newtxt = string.replace(dst_newtxt, '@%s@' % strKey, tValue)

    # Write the target file only if the current text differs from the file
    # contents.
    if dst_newtxt != dst_oldtxt:
        # Overwrite the file.
        dst_file = open(target[0].get_path(), 'w')
        dst_file.write(dst_newtxt)
        dst_file.close()


def filter_emitter(target, source, env):
    if 'SUBSTITUTIONS' in env:
        atSubstitutions = dict(env['SUBSTITUTIONS'])
    else:
        atSubstitutions = {}

    # Loop over all replacements and add them to the dependencies.
    for strKey, tValue in atSubstitutions.items():
        env.Depends(
            target,
            SCons.Node.Python.Value('%s:%s' % (strKey, tValue))
        )

    return target, source


def filter_string(target, source, env):
    return 'Filter %s' % target[0].get_path()


def ApplyToEnv(env):
    # ---------------------------------------------------------------------------
    #
    # Add the filter builder.
    #
    tAct = SCons.Action.Action(
        filter_action,
        filter_string
    )
    tBld = SCons.Script.Builder(
        action=tAct,
        emitter=filter_emitter,
        single_source=1
    )
    env['BUILDERS']['Filter'] = tBld
