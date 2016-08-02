# -*- coding: utf-8 -*-


import os.path
import string
import xml.dom.minidom

from SCons.Script import *


def hboot_snippet_action(target, source, env):
    atParameter = env['PARAMETER']

    # Create a new XML document.
    tXml = xml.dom.minidom.getDOMImplementation().createDocument(None, 'HBootSnippet', None)
    # Get the root element.
    tNodeRoot = tXml.documentElement

    # Create the "Info" node.
    tNodeInfo = tXml.createElement('Info')
    tNodeInfo.setAttribute('group', str(atParameter['group']))
    tNodeInfo.setAttribute('artifact', str(atParameter['artifact']))
    tNodeInfo.setAttribute('version', str(atParameter['version']))
    tNodeInfo.setAttribute('vcs-id', str(atParameter['vcs-id']))
    tNodeRoot.appendChild(tNodeInfo)

    # Create the "License" node.
    tNodeLicense = tXml.createElement('License')
    tNodeLicense.setAttribute('name', str(atParameter['license']))
    tNodeInfo.appendChild(tNodeLicense)

    # Create the "Author" node.
    tNodeAuthor = tXml.createElement('Author')
    tNodeAuthor.setAttribute('name', str(atParameter['author_name']))
    tNodeAuthor.setAttribute('url', str(atParameter['author_url']))
    tNodeInfo.appendChild(tNodeAuthor)

    # Create the "Description" node.
    tNodeDescription = tXml.createElement('Description')
    tNodeDescription.appendChild(tXml.createTextNode(str(atParameter['description'])))
    tNodeInfo.appendChild(tNodeDescription)

    # Append all categories.
    for strCategory in atParameter['categories']:
        tNodeCategory = tXml.createElement('Category')
        tNodeCategory.appendChild(tXml.createTextNode(str(strCategory)))
        tNodeInfo.appendChild(tNodeCategory)

    # Load the contents of the source file.
    strInput = source[0].get_contents()

    # Add a "Snippet" node.
    tNodeSnippet = tXml.createElement('Snippet')
    tNodeSnippet.appendChild(tXml.createTextNode(str(strInput)))
    tNodeRoot.appendChild(tNodeSnippet)

    # Write the result to the target file.
    tOutputFile = open(target[0].get_path(), 'wt')
    tXml.writexml(tOutputFile, indent='', addindent='\t', newl='\n', encoding='utf-8')
    tOutputFile.close()

    return 0


def hboot_snippet_emitter(target, source, env):
    # Depend on all values for the template.
    for strKey, strValue in env['PARAMETER'].iteritems():
        env.Depends(target, SCons.Node.Python.Value('%s:%s' % (strKey, strValue)))

    return target, source


def hboot_snippet_string(target, source, env):
    return 'HBootSnippet %s' % target[0].get_path()


def ApplyToEnv(env):
    #-------------------------------------------------------------------------
    #
    # Add HBootSnippet builder.
    #
    env['PARAMETER'] = {}
    hboot_snippet_act = SCons.Action.Action(hboot_snippet_action, hboot_snippet_string)
    hboot_snippet_bld = Builder(action=hboot_snippet_act, emitter=hboot_snippet_emitter, suffix='.xml')
    env['BUILDERS']['HBootSnippet'] = hboot_snippet_bld

