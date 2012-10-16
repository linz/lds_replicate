<?xml version="1.0" encoding="ISO-8859-1"?>
<xsl:stylesheet version="1.0" 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://www.opengis.net/wfs" 
  xmlns:wfs="http://www.opengis.net/wfs"
  xmlns:ows="http://www.opengis.net/ows"
>
<xsl:output method="text"/>
<xsl:strip-space elements="*"/>

<xsl:template match="wfs:WFS_Capabilities">
	<xsl:apply-templates/>
</xsl:template>

<xsl:template match="wfs:FeatureTypeList">
	<xsl:text>[&#xa;</xsl:text>
	<xsl:for-each select="wfs:FeatureType">
		<xsl:sort select="wfs:Name"/>
		<xsl:text>["</xsl:text><xsl:value-of select="normalize-space(wfs:Name)"/><xsl:text>",</xsl:text>
		<xsl:text>"id",</xsl:text>
		<xsl:text>"</xsl:text><xsl:value-of select="normalize-space(wfs:Title)"/><xsl:text>",</xsl:text>
		<xsl:text>[</xsl:text>
		<xsl:for-each select="ows:Keywords/ows:Keyword">
				<xsl:text>"</xsl:text>
				<xsl:value-of select="normalize-space(.)"/>
				<xsl:choose>
					<xsl:when test="position() != last()">
						<xsl:text>",</xsl:text>
					</xsl:when>
					<xsl:otherwise>
						<xsl:text>"],</xsl:text>
					</xsl:otherwise>
				</xsl:choose>
		</xsl:for-each>
		<xsl:text>"",</xsl:text>
		<xsl:text>"shape",</xsl:text>
		<xsl:text>"",</xsl:text>
		<xsl:text>"",</xsl:text>
		<xsl:choose>
			<xsl:when test="position() != last()">
				<xsl:text>""],&#xa;</xsl:text>
			</xsl:when>
			<xsl:otherwise>
				<xsl:text>""]&#xa;</xsl:text>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:for-each>
	<xsl:text>]&#xa;</xsl:text>
</xsl:template>

<xsl:template match="*">
    <xsl:message terminate="no">
        WARNING: Unmatched element: <xsl:value-of select="name()"/>
    </xsl:message>
</xsl:template>

</xsl:stylesheet>