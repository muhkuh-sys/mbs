# -*- coding: utf-8 -*-

import SCons

import xml.dom.minidom


# Init the filename->revision dictionary.
aArtifacts = dict({})


def add_artifact(tEnv, tFiles, tServer, strGroupID, strArtifactID, strVersion,
                 strPackaging, **kwargs):
    bGood = kwargs.get('GOOD', True)

    if bGood is True:
        # Process all files.
        for tFile in tFiles:
            # Combine all server attributes to a hashable string.
            strServerID = tServer[0] + '\0' + tServer[1] + '\0' + tServer[2]
            if strServerID not in aArtifacts:
                aArtifacts[strServerID] = dict({})
            aServer = aArtifacts[strServerID]

            if strGroupID not in aServer:
                aServer[strGroupID] = dict({})
            aGroup = aServer[strGroupID]

            # Combine the artifact ID and the packaging to get a unique
            # packege ID.
            strPackageID = strArtifactID + '\0' + strPackaging
            if strPackageID in aGroup:
                raise Exception(
                    'Double defined artifact "%s" with packaging "%s" '
                    'in group "%s"!' % (
                        strArtifactID,
                        strPackaging,
                        strGroupID
                    )
                )

            aGroup[strPackageID] = dict({
                'artifact': strArtifactID,
                'file': tFile,
                'version': strVersion,
                'packaging': strPackaging
            })


def artifact_action(target, source, env):
    tXmlData = xml.dom.minidom.getDOMImplementation().createDocument(
        None,
        "Artifacts",
        None
    )
    tNode_Project = tXmlData.documentElement.appendChild(
        tXmlData.createElement('Project')
    )

    # Loop over all artifacts.
    for (strServerID, atGroups) in aArtifacts.items():
        # Split the server ID in the 3 components.
        aAttribServer = strServerID.split('\0')

        # Create the "Server" element with all attributes.
        tNode_Server = tNode_Project.appendChild(
            tXmlData.createElement('Server')
        )
        tNode_Server.setAttribute('id', aAttribServer[0])
        tNode_Server.setAttribute('release', aAttribServer[1])
        tNode_Server.setAttribute('snapshots', aAttribServer[2])

        for (strGroupID, atFiles) in atGroups.items():
            for (strPackageID, tFileAttribs) in atFiles.items():
                # Create a new Target node with the path to the file as
                # 'file' attribute.
                tNode_Target = tNode_Server.appendChild(
                    tXmlData.createElement('Target')
                )
                tNode_Target.setAttribute(
                    'file',
                    tFileAttribs['file'].get_path()
                )
                # Create ArtifactID, GroupID and Packaging children.
                tNode_ArtifactID = tNode_Target.appendChild(
                    tXmlData.createElement('ArtifactID')
                )
                tNode_ArtifactID.appendChild(
                    tXmlData.createTextNode(tFileAttribs['artifact'])
                )
                tNode_GroupID = tNode_Target.appendChild(
                    tXmlData.createElement('GroupID')
                )
                tNode_GroupID.appendChild(tXmlData.createTextNode(strGroupID))
                tNode_Version = tNode_Target.appendChild(
                    tXmlData.createElement('Version')
                )
                tNode_Version.appendChild(
                    tXmlData.createTextNode(tFileAttribs['version'])
                )
                tNode_Packaging = tNode_Target.appendChild(
                    tXmlData.createElement('Packaging')
                )
                tNode_Packaging.appendChild(
                    tXmlData.createTextNode(tFileAttribs['packaging'])
                )

    # Write the file to the target.
    tFile = open(target[0].get_path(), 'wt')
    tXmlData.writexml(
        tFile,
        indent='',
        addindent='\t',
        newl='\n',
        encoding='UTF-8'
    )
    tFile.close()

    return None


def artifact_emitter(target, source, env):
    # Loop over all elements in the 'aArtifacts' dictionary and make the
    # target depend on them.
    for (strServerID, atGroups) in aArtifacts.items():
        for (strGroupID, atFiles) in atGroups.items():
            for (strPackageID, tFileAttribs) in atFiles.items():
                env.Depends(target, tFileAttribs['file'])
                # Combine the file name with the server, group and artifact ID.
                aHash = [
                    strServerID,
                    strGroupID,
                    tFileAttribs['artifact'],
                    tFileAttribs['file'].get_path(),
                    tFileAttribs['packaging']
                ]
                env.Depends(target, SCons.Node.Python.Value('\0'.join(aHash)))

    return target, source


def artifact_string(target, source, env):
    return 'Artifact %s' % target[0].get_path()


def ApplyToEnv(env):
    # ---------------------------------------------------------------------------
    #
    # Add artifact builder.
    #

    artifact_act = SCons.Action.Action(artifact_action, artifact_string)
    artifact_bld = SCons.Script.Builder(
        action=artifact_act,
        emitter=artifact_emitter,
        suffix='.xml'
    )
    # TODO: Do not add the ArtifactInt builder to the global list.
    env['BUILDERS']['Artifact'] = artifact_bld

    # Provide the 'Artifact' method.
    env.AddMethod(add_artifact, 'AddArtifact')
