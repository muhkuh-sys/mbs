<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" indent="no" omit-xml-declaration="yes" encoding="UTF-8"/>

<xsl:template match="/">
	<html>
		<xsl:comment>XSLT stylesheet used to transform this file:  setup2html.xsl</xsl:comment>
		<xsl:apply-templates select="muhkuh_buildsystem"/>
	</html>
</xsl:template>

<xsl:template match="muhkuh_buildsystem">
	<head>
		<title>Muhkuh Build System for project "<xsl:value-of select="@project"/>"</title>
	</head>
	<body bgcolor="#ffffff" marginheight="2" marginwidth="2" topmargin="2" leftmargin="2">

	<table border="1" cellspacing="0" cellpadding="2">
		<tr>
			<td valign="TOP" width="20%">
				<h2><a name="toc">Table of Contents</a></h2>
				<b><big><a href="#project">Project Information</a></big></b><br/><br/>
				<b><big><a href="#repositories">Repositories</a></big></b><br/>
				<b><big><a href="#scons">Scons</a></big></b><br/>
				<b><big><a href="#tools">Tools</a></big></b><br/>
				<b><big><a href="#filters">Filters</a></big></b><br/>
			</td>
		</tr>

		<tr><td>
			<table border="0" cellspacing="0" cellpadding="5">
				<tr>
					<td colspan="3">
						<a name="project"/>
						<b><big>Project Information</big></b>
					</td>
				</tr>
				<tr>
					<td width="5%"/>
					<td valign="BOTTOM" width="25%">
						<b>Name:</b>
					</td>
					<td valign="BOTTOM" width="70%">
						<xsl:value-of select="@project"/>
					</td>
				</tr>
				<tr>
					<td width="5%"/>
					<td valign="BOTTOM" width="25%">
						<b>Version:</b>
					</td>
					<td valign="BOTTOM" width="70%">
						<xsl:value-of select="project_version/major"/>.<xsl:value-of select="project_version/minor"/>
					</td>
				</tr>
				<tr>
					<td width="5%"/>
					<td valign="BOTTOM" width="25%">
						<b>Marker directory:</b>
					</td>
					<td valign="BOTTOM" width="70%">
						<tt><xsl:value-of select="paths/marker"/></tt>
					</td>
				</tr>
				<tr>
					<td width="5%"/>
					<td valign="BOTTOM" width="25%">
						<b>Repository directory:</b>
					</td>
					<td valign="BOTTOM" width="70%">
						<tt><xsl:value-of select="paths/repository"/></tt>
					</td>
				</tr>
				<tr>
					<td width="5%"/>
					<td valign="BOTTOM" width="25%">
						<b>Depack directory:</b>
					</td>
					<td valign="BOTTOM" width="70%">
						<tt><xsl:value-of select="paths/depack"/></tt>
					</td>
				</tr>
			</table>
		</td></tr>


		<tr><td>
			<table border="0" cellspacing="0" cellpadding="5">
				<tr>
					<td colspan="3">
						<a name="repositories"/>
						<b><big>Repositories</big></b>
					</td>
				</tr>

				<xsl:for-each select="repositories/repository">
					<xsl:sort select="@name"/>
					<xsl:element name="td">
						<xsl:attribute name="width">
							"5%"
						</xsl:attribute>
					</xsl:element>
					<xsl:element name="td">
						<xsl:attribute name="valign">
							"BOTTOM"
						</xsl:attribute>
						<xsl:attribute name="width">
							"25%"
						</xsl:attribute>
						<b><xsl:value-of select="@name"/>:</b>
					</xsl:element>
					<xsl:element name="td">
						<xsl:attribute name="valign">
							"BOTTOM"
						</xsl:attribute>
						<xsl:attribute name="width">
							"70%"
						</xsl:attribute>
						<xsl:element name="a">
							<xsl:attribute name="href">
								<xsl:value-of select="."/>
							</xsl:attribute>
							<xsl:value-of select="."/>
						</xsl:element>
					</xsl:element>
					<br/>
				</xsl:for-each>
			</table>
		</td></tr>


		<tr><td>
			<table border="0" cellspacing="0" cellpadding="5">
				<tr>
					<td colspan="5">
						<a name="scons"/>
						<b><big>Scons</big></b>
					</td>
				</tr>
				<tr>
					<th>Group</th>
					<th>Name</th>
					<th>Version</th>
					<th>Typ</th>
					<th>Folder</th>
				</tr>
				<tr>
					<td>
						<xsl:value-of select="scons/group"/>
					</td>
					<td>
						<xsl:value-of select="scons/name"/>
					</td>
					<td>
						<xsl:value-of select="scons/version"/>
					</td>
					<td>
						<xsl:value-of select="scons/typ"/>
					</td>
					<td>
						<xsl:value-of select="scons/folder"/>
					</td>
				</tr>
			</table>
		</td></tr>


		<tr><td>
			<table border="0" cellspacing="0" cellpadding="5">
				<tr>
					<td colspan="5">
						<a name="tools"/>
						<b><big>Tools</big></b>
					</td>
				</tr>
				<tr>
					<th>Name</th>
					<th>Group</th>
					<th>Version</th>
					<th>Typ</th>
					<th>Folder</th>
				</tr>
				<xsl:for-each select="tools/tool">
					<xsl:sort select="name"/>
					<xsl:element name="tr">
						<xsl:element name="td">
							<xsl:value-of select="name"/>
						</xsl:element>
						<xsl:element name="td">
							<xsl:value-of select="group"/>
						</xsl:element>
						<xsl:element name="td">
							<xsl:value-of select="version"/>
						</xsl:element>
						<xsl:element name="td">
							<xsl:value-of select="typ"/>
						</xsl:element>
						<xsl:element name="td">
							<xsl:value-of select="folder"/>
						</xsl:element>
					</xsl:element>
				</xsl:for-each>
			</table>
		</td></tr>


		<tr><td>
			<table border="0" cellspacing="0" cellpadding="5">
				<tr>
					<td colspan="2">
						<a name="filters"/>
						<b><big>Filters</big></b>
					</td>
				</tr>
				<tr>
					<th>Template</th>
					<th>Destination</th>
				</tr>
				<xsl:for-each select="filters/filter">
					<xsl:sort select="template"/>
					<xsl:element name="tr">
						<xsl:element name="td">
							<xsl:value-of select="template"/>
						</xsl:element>
						<xsl:element name="td">
							<xsl:value-of select="destination"/>
						</xsl:element>
					</xsl:element>
				</xsl:for-each>
			</table>
		</td></tr>
	</table>

	</body>
</xsl:template>

</xsl:stylesheet>
