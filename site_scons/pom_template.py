# -*- coding: utf-8 -*-


import codecs
import string

import SCons.Action
import SCons.Script
import SCons.Node.Python


def pom_template_action(target, source, env):
    aSubst = dict({
        'GROUP': str(env['POM_TEMPLATE_GROUP']),
        'ARTIFACT': str(env['POM_TEMPLATE_ARTIFACT']),
        'VERSION': str(env['POM_TEMPLATE_VERSION']),
        'PACKAGING': str(env['POM_TEMPLATE_PACKAGING'])
    })

    # Read the template.
    tFile = codecs.open(source[0].get_path(), 'r')
    strTemplate = tFile.read()
    tFile.close()

    tTemplate = string.Template(strTemplate)
    strPOM = tTemplate.substitute(aSubst)

    # Write the POM to the target file.
    tFile = codecs.open(target[0].get_path(), 'w', 'utf-8')
    tFile.write(strPOM)
    tFile.close()

    return 0


def pom_template_emitter(target, source, env):
    # Make the target depend on the POM fields.
    env.Depends(target, SCons.Node.Python.Value(SCons.Script.PROJECT_VERSION))
    env.Depends(target, SCons.Node.Python.Value(env['POM_TEMPLATE_GROUP']))
    env.Depends(target, SCons.Node.Python.Value(env['POM_TEMPLATE_ARTIFACT']))
    env.Depends(target, SCons.Node.Python.Value(env['POM_TEMPLATE_VERSION']))
    env.Depends(target, SCons.Node.Python.Value(env['POM_TEMPLATE_PACKAGING']))

    return target, source


def pom_template_string(target, source, env):
    return 'POMTemplate %s' % target[0].get_path()


def ApplyToEnv(env):
    #----------------------------------------------------------------------------
    #
    # Add POMTemplate builder.
    #
    env['POM_TEMPLATE_GROUP'] = ''
    env['POM_TEMPLATE_ARTIFACT'] = ''
    env['POM_TEMPLATE_VERSION'] = ''
    env['POM_TEMPLATE_PACKAGING'] = ''
    pom_template_act = SCons.Action.Action(pom_template_action, pom_template_string)
    pom_template_bld = SCons.Script.Builder(action=pom_template_act, emitter=pom_template_emitter, single_source=1)
    env['BUILDERS']['POMTemplate'] = pom_template_bld
