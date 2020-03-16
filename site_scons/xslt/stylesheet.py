import xml.dom
import xslt.core
import xslt.elements
import xslt.exceptions
import xslt.properties
import xslt.serializer
import xslt.tools


class Stylesheet(object):
    def __init__(self, uriOrDoc=None, dp=xslt.core.DocumentProvider()):
        self.dp = dp

        if isinstance(uriOrDoc, xml.dom.Node):
            if uriOrDoc.nodeType != xml.dom.Node.DOCUMENT_NODE:
                uriOrDoc = uriOrDoc.ownerDocument
            uriOrDoc = self.dp.addDOMDocument(doc)

        doc = self.dp.document(uriOrDoc)

        self.stripSpace = []
        self.preserveSpace = []
        self.output = {}
        self.keys = {}
        self.decimalFormats = {}
        self.attrSets = {}
        self.namespaceAliases = {}

        self.variables = {}
        self.templates = []  # not used
        self.patterns = {(None, None): []}
        self.namedTemplates = {}
        self.imports = []

        self._parseStylesheetContent(doc, uriOrDoc)
        for i in self.patterns:
            self.patterns[i].sort(key=lambda x: x[2])

        self.imports.reverse()
        for imp in self.imports:  # descending import precedence
            xslt.tools.safeUpdateDict(
                self.variables,
                imp.variables
            )
            xslt.tools.safeUpdateDict(
                self.namespaceAliases,
                imp.namespaceAliases
            )
            xslt.tools.mergeNameTestLists(
                self.stripSpace,
                imp.stripSpace,
                self.stripSpace + self.preserveSpace
            )
            xslt.tools.mergeNameTestLists(
                self.preserveSpace,
                imp.preserveSpace,
                self.stripSpace + self.preserveSpace
            )
            xslt.tools.combineOutput(self.output, imp.output)
            for key in imp.keys.values():
                self.addKey(key)

    def transform(self, uriOrDoc, context):
        if isinstance(uriOrDoc, xml.dom.Node):
            if uriOrDoc.nodeType != xml.dom.Node.DOCUMENT_NODE:
                uriOrDoc = uriOrDoc.ownerDocument
            uriOrDoc = self.dp.addDOMDocument(doc)

        doc = self.dp.document(uriOrDoc)

        xslt.tools.stripSpace(
            doc,
            self.stripSpace,
            self.preserveSpace,
            defaultStrip=False
        )

        result = self.dp.createDocument().createDocumentFragment()
        context.nodeset = [doc]
        context.result = result

        for i, v in self.variables.items():
            v.instantiate(context)

        self.applyTemplates(context, (None, None))

        return result

    def transformToDoc(self, *args):
        frag = self.transform(*args)
        doc = frag.ownerDocument
        doc.appendChild(frag)
        xslt.core.fixNamespaces(doc)
        return doc

    def transformToString(self, *args):
        frag = self.transform(*args)
        xslt.core.fixNamespaces(frag)

        method = self.output.get('method', (None, 'xml'))
        if method == (None, 'xml'):
            ser = xslt.serializer.XMLSerializer(self.output)
        elif method == (None, 'text'):
            ser = xslt.serializer.TextSerializer(self.output)
        elif method == (None, 'html'):
            ser = xslt.serializer.XMLSerializer(self.output)
        else:
            ser = None

        if ser is not None:
            return ser.serializeResult(frag)
        else:
            return ''

    def _parseStylesheetContent(self, doc, baseUri):
        sheet = doc.documentElement
        if(
            sheet.namespaceURI != xslt.core.XSLT_NAMESPACE or
            not(
                sheet.localName == 'stylesheet' or
                sheet.localName == 'transform'
            )
        ):
            raise xslt.exceptions.UnexpectedNode(doc.documentElement)

        # compile options (that are specified as xsl:stylesheet attributes)
        # are valid only within this stylesheet
        # (not include and imports) [XSLT 7.1.1], [XSLT 14.1]
        options = {}
        options['forwardsCompatible'] = sheet.getAttribute('version') != '1.0'
        options['namespaces'] = xslt.tools.getNamespaceBindings(sheet)
        options['extensionElementsNS'] = xslt.properties.nsListProperty(
            sheet,
            'extension-element-prefixes',
            namespaces=options['namespaces']
        ) or []
        options['excludeResultNS'] = xslt.properties.nsListProperty(
            sheet,
            'exclude-result-prefixes',
            namespaces=options['namespaces']
        ) or []
        options['baseUri'] = baseUri
        options['definedVars'] = []
        xslt.tools.stripSpace(
            sheet,
            preserveSpaceList=[(xslt.core.XSLT_NAMESPACE, 'text')]
        )

        for i in range(sheet.childNodes.length):
            node = sheet.childNodes.item(i)
            if node.nodeType != xml.dom.Node.ELEMENT_NODE:
                continue

            # Ignore top-level elements with an unknown non-null
            # namespace [XSLT 2.2]
            if node.namespaceURI != xslt.core.XSLT_NAMESPACE:
                if node.namespaceURI is None:
                    raise xslt.exceptions.UnexpectedNode(
                        doc.documentElement.tagName
                    )
                continue

            if node.localName == 'import':
                # TODO: check that imports come first
                href = xslt.properties.stringProperty(
                    node,
                    'href',
                    required=True
                )
                self.imports.append(Stylesheet(href, dp=self.dp))

            if node.localName == 'include':
                href = xslt.properties.stringProperty(
                    node,
                    'href',
                    required=True
                )
                self._parseStylesheetContent(
                    self.dp.document(href, baseUri),
                    self.dp.absUri(href, baseUri)
                )

            if node.localName == 'variable' or node.localName == 'param':
                if node.localName == 'param':
                    varclass = xslt.elements.Param
                else:
                    varclass = xslt.elements.Variable
                var = varclass(node, self, options)
                self.variables[var.name] = var

            if node.localName == 'template':
                template = xslt.elements.Template(node, self, options)
                self.addTemplateRule(template)

            if node.localName == 'strip-space':
                space = xslt.elements.SpaceStripping(node)
                self.stripSpace.extend(space.nameTests())

            if node.localName == 'preserve-space':
                space = xslt.elements.SpaceStripping(node)
                self.preserveSpace.extend(space.nameTests())

            if node.localName == 'output':
                output = xslt.elements.Output(node, self, options)
                xslt.tools.combineOutput(self.output, output.outputDict())

            if node.localName == 'key':
                key = xslt.elements.Key(node, self, options)
                self.addKey(key)

            if node.localName == 'decimal-format':
                raise xslt.exceptions.NotImplemented(node.localName)

            if node.localName == 'namespace-alias':
                alias = xslt.elements.NamespaceAlias(node, self, options)
                ss, res = alias.getTuple()
                # accept one that occurs last
                self.namespaceAliases[ss] = res

            if node.localName == 'attribute-set':
                aset = xslt.elements.AttributeSet(node, self, options)
                if aset.name in self.attrSets:
                    self.attrSets[aset.name].update(aset)
                else:
                    self.attrSets[aset.name] = aset

    def addKey(self, key):
        if key.name in self.keys.has_key:
            self.keys[key.name].update(key)
        else:
            self.keys[key.name] = key

    def instantiateAttributeSet(self, context, name):
        """Instantiate attribute set by name.
        Attributte-sets from imported stylesheets are applyed"""

        for imp in self.imports:
            imp.instantiateAttributeSet(context, name)

        attrSet = self.attrSets.get(name)
        if attrSet:
            attrSet.instantiate(context)

    def getNamespaceAlias(self, uri):
        """Try to remap namespaceURI using defined alises.
        If no alias is specified for a URI just return passes URI."""

        return self.namespaceAliases.get(uri, uri)

    def addTemplateRule(self, template):
        self.templates.append(template)

        if template.name is not None:
            if template.name in self.namedTemplates:
                raise xslt.exceptions.DuplicateName
            name = template.name
            self.namedTemplates[name] = template

        elif template.patterns is not None:
            patterns = template.patterns
            mode = template.mode
            if mode not in self.patterns:
                self.patterns[mode] = []
            self.patterns[mode] += patterns

    def initMode(self, context, mode):
        self._matchAll(context, mode)
        for i in self.imports:
            i.initMode(context, mode)

    def _matchAll(self, context, mode):
        document = (
            context.node.ownerDocument
            if context.node.nodeType != xml.dom.Node.DOCUMENT_NODE
            else context.node
        )

        handle = (hash(self), hash(document), mode)

        if handle in context.matches:
            # already matched this stylesheet agains current document and
            # current mode
            return

        patterns = self.patterns[mode]
        matches = {}
        nsCopy = context.namespaces.copy()
        for (pattern, template, priority) in patterns:
            context.namespaces.update(template.namespaces)
            nodes = template.match.nodes(context)
            for node in nodes:
                matches[hash(node)] = template

        context.matches[handle] = matches

    def applyTemplates(self, context, mode):
        for node in context:
            self.applyTemplatesImpl(context, mode)

    def applyImports(self, context):
        if context.cause == (None, None):
            # top-level element or for-each
            return

        for i in self.imports:
            if context.cause[0] is None:
                r = i.applyTemplatesImpl(context, context.cause[1])
            else:
                r = i.callTemplate(context, context.cause[0])

            if r:
                return True

    def applyTemplatesImpl(self, context, mode):
        self.initMode(context, mode)

        context.cause = (None, mode)
        node = context.node
        doc = (
            context.node.ownerDocument
            if context.node.nodeType != xml.dom.Node.DOCUMENT_NODE
            else context.node
        )
        handle = (hash(self), hash(doc), mode)
        if hash(node) in context.matches[handle]:
            context.matches[handle][hash(node)].instantiate(context)
            return True
        else:
            r = self.applyImports(context)
            if r:
                return True

        # non top-level stylesheet
        if self != context.stylesheet:
            return False

        # else built-ins in top-level
        if(
            context.node.nodeType == xml.dom.Node.ELEMENT_NODE or
            context.node.nodeType == xml.dom.Node.DOCUMENT_NODE
        ):
            if node.childNodes.length > 0:
                subContext = context.copy()
                subContext.nodeset = list(node.childNodes)
                self.applyTemplates(subContext, mode)
        elif(
            context.node.nodeType == xml.dom.Node.TEXT_NODE or
            context.node.nodeType == xml.dom.Node.CDATA_SECTION_NODE or
            node.nodeType == xml.dom.Node.ATTRIBUTE_NODE
        ):
            context.pushResult(context.node)
        # OK: <xsl:template match="processing-instruction()|comment()"/>
        # OK: The built-in template rule for namespace nodes is also to
        #     do nothing

    def callTemplate(self, context, name):
        context.cause = (name, None)
        if name in self.namedTemplates:
            self.namedTemplates[name].instantiate(context)
            return True
        else:
            self.applyImports(context)
            if self != context.stylesheet:  # non top-level
                return False

            raise xslt.exceptions.NotFound
