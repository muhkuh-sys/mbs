import xml.dom
import xslt.tools
import xslt.properties
import xslt.xp
from io import StringIO
import xslt.properties
import xslt.core
import xpath.tools
import functools


class LiteralText(xslt.core.Element):
    """Compatible with Element to be an XSLT tree node.
    Represents a text from the stylesheet that needs just to be copied to
    result tree."""

    name = '_literal_text'

    def __init__(self, node, stylesheet, options):
        self.text = node.data

    def instantiate(self, context):
        context.pushResult(self.text)


class LiteralElement(xslt.core.Element):
    name = '_literal_element'

    def initImpl(self, element, stylesheet, options):
        self.name = (element.prefix, element.localName)
        self.ns = element.namespaceURI
        self.useSets = xslt.properties.qnameListProperty(
            element,
            (xslt.core.XSLT_NAMESPACE, 'use-attribute-sets'),
            namespaces=options['namespaces'],
            default='',
            resolveDefault=False
        )

        options['excludeResultNS'].extend(
            xslt.properties.nsListProperty(
                element,
                (xslt.core.XSLT_NAMESPACE, 'exclude-result-prefixes'),
                namespaces=options['namespaces']
            ) or []
        )
        options['extensionElementsNS'].extend(xslt.properties.nsListProperty(
            element,
            'extension-element-prefixes',
            namespaces=options['namespaces']
        ) or [])
        if(
            xslt.properties.stringProperty(
                element,
                (xslt.core.XSLT_NAMESPACE, 'version'),
                default='1.0'
            ) != '1.0'
        ):
            options['forwardsCompatible'] = True
        if(
            xslt.properties.stringProperty(
                element,
                (xslt.core.XSLT_NAMESPACE, 'version')
            ) == '1.0'
        ):
            options['forwardsCompatible'] = False

        self.attrs = {}
        for i in range(element.attributes.length):
            attr = element.attributes.item(i)

            if attr.namespaceURI == xslt.core.XSLT_NAMESPACE:
                # do not copy xsl: attributes
                continue

            if attr.namespaceURI == xml.dom.XMLNS_NAMESPACE:
                # check if this namespace node is excluded
                localName = None
                if attr.localName != 'xmlns':
                    localName = attr.localName
                nsUri = xslt.properties.resolveNamespace(
                    localName,
                    options['namespaces'],
                    resolveDefault=True
                )
                if nsUri in options['excludeResultNS']:
                    continue

            self.attrs[
                (attr.prefix, attr.localName, attr.namespaceURI)
            ] = xslt.xp.AttributeTemplate(attr.value)

        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        ss = context.stylesheet
        e = context.resultDocument.createElementNS(
            ss.getNamespaceAlias(self.ns),
            xslt.tools.formatQName(self.name)
        )

        for attrSet in self.useSets:
            ss.instantiateAttributeSet(context, attrSet)

        for (k, v) in self.attrs.items():
            if k[2] == xml.dom.XMLNS_NAMESPACE:
                e.setAttributeNS(
                    k[2],
                    'xmlns:%s' % k[1],
                    ss.getNamespaceAlias(v.value(context))
                )
            else:
                e.setAttributeNS(
                    ss.getNamespaceAlias(k[2]),
                    xslt.tools.formatQName(k[0:2]),
                    v.value(context)
                )

        context.pushResult(e)
        context.result = e
        self.instantiateContent(context)


class PerformFallback(xslt.core.Element):
    name = '_perform_fallback'

    def initImpl(self, element, stylesheet, options):
        fallbacks = filter(
            lambda x: (
                x.namespaceURI == xslt.core.XSLT_NAMESPACE and
                x.localName == 'fallback'
            ), xslt.tools.childElements(element)
        )
        self.setContent(fallbacks, stylesheet, options)

    def instantiateImpl(self, context):
        context.fallback = True
        self.instantiateContent(context)


class Output(xslt.core.Element):
    name = 'output'

    def initImpl(self, node, stylesheet, options):
        output = {}

        if node.hasAttribute('method'):
            output['method'] = xslt.properties.qnameProperty(
                node,
                'method',
                namespaces=options['namespaces'],
                resolveDefault=False
            )
        if node.hasAttribute('indent'):
            output['indent'] = xslt.properties.boolProperty(
                node,
                'indent'
            )
        if node.hasAttribute('encoding'):
            output['encoding'] = xslt.properties.stringProperty(
                node,
                'encoding'
            )
        if node.hasAttribute('version'):
            output['version'] = xslt.properties.stringProperty(
                node,
                'version'
            )
        if node.hasAttribute('standalone'):
            output['standalone'] = xslt.properties.boolProperty(
                node,
                'standalone'
            )
        if node.hasAttribute('omit-xml-declaration'):
            output['omit-xml-declaration'] = xslt.properties.boolProperty(
                node,
                'omit-xml-declaration'
            )
        if node.hasAttribute('doctype-system'):
            output['doctype-system'] = xslt.properties.stringProperty(
                node,
                'doctype-system'
            )
        if node.hasAttribute('doctype-public'):
            output['doctype-public'] = xslt.properties.stringProperty(
                node,
                'doctype-public'
            )
        if node.hasAttribute('cdata-section-elements'):
            output['cdata-section-elements'] = set(
                xslt.properties.qnameListProperty(
                    node,
                    'cdata-section-elements',
                    namespaces=options['namespaces'],
                    resolveDefault=True
                )
            )
        if node.hasAttribute('media-type'):
            output['media-type'] = xslt.properties.stringProperty(
                node,
                'media-type'
            )

        self.output = output

        xslt.core.assertEmptyNode(node)

    def outputDict(self):
        return self.output


class SpaceStripping(xslt.core.Element):
    def initImpl(self, element, stylesheet, options):
        self.nametests = xslt.properties.nameTestListProperty(
            element,
            'elements',
            namespaces=options['namespaces'],
            resolveDefault=True,
            required=True
        )
        xslt.core.assertEmptyNode(element)

    def nameTests(self):
        return self.nametests


class NamespaceAlias(xslt.core.Element):
    name = 'namespace-alias'

    def initImpl(self, element, stylesheet, options):
        stylesheetUri = xslt.properties.nsPrefixProperty(
            element,
            'stylesheet-prefix',
            namespaces=options['namespaces'],
            required=True
        )
        resultUri = xslt.properties.nsPrefixProperty(
            element,
            'result-prefix',
            namespaces=options['namespaces'],
            required=True
        )
        self.t = (stylesheetUri, resultUri)
        xslt.core.assertEmptyNode(element)

    def getTuple(self):
        return self.t


class AttributeSet(xslt.core.Element):
    name = 'attribute-set'

    def initImpl(self, node, stylesheet, options):
        self.name = xslt.properties.qnameProperty(
            node,
            'name',
            required=True,
            namespaces=options['namespaces'],
            resolveDefault=False
        )
        self.useSets = xslt.properties.qnameListProperty(
            node,
            'use-attribute-sets',
            namespaces=options['namespaces'],
            default='',
            resolveDefault=False
        )
        attrs = xslt.core.xsltChildren(node, allowedNames='attribute')
        self.attributes = dict((attr.name, attr) for attr in attrs)

    def update(self, attrSet):
        """Add attribute definitions from attrSet,
        replacing existing attributes."""

        self.attributes.update(attrSet.attributes)
        self.useSets += attrSet.useSets

    def instantiateImpl(self, context):
        context.variables = context.toplevelContext.variables.copy()

        for attrSet in self.useSets:
            context.stylesheet.instantiateAttributeSet(context, attrSet)

        for a in self.attributes:
            a.instantiate(context)


class Key(xslt.core.Element):
    name = 'Key'

    def initImpl(self, node, stylesheet, options):
        self.name = xslt.properties.qnameProperty(
            node,
            'name',
            required=True,
            namespaces=options['namespaces'],
            resolveDefault=False
        )
        match = xslt.properties.patternProperty(node, 'match', required=True)
        use = xslt.properties.exprProperty(node, 'user', required=True)
        self.keys = (match, use)

    def update(self, key):
        self.keys.extend(key.keys)

    def select(self, context, value):
        subContext = context.toplevelContext.copy()
        nodes = []
        for key in self.keys:
            cands = key[0].nodes(subContext)
            for cand in cands:
                subContext.nodeset = [cand]
                if key[1].findString(subContext) == \
                   xpath.tools.string(value, context):
                    nodes.append(cand)

        return nodes


class Template(xslt.core.Element):
    name = 'template'

    def initImpl(self, element, stylesheet, options):
        self.mode = xslt.properties.qnameProperty(
            element,
            'mode'
        ) or (None, None)
        self.name = xslt.properties.qnameProperty(element, 'name')
        self.match = xslt.properties.patternProperty(element, 'match')
        self.priority = xslt.properties.floatProperty(element, 'priority')

        self.patterns = None
        if self.match is not None:
            # split union pattern and  compute priority for each one
            patterns = xslt.tools.splitUnionExpr(self.match.expr)
            self.patterns = [
                (
                    xslt.xp.Pattern(p),
                    self,
                    xslt.tools.computeDefaultPriority(p)
                    if self.priority is None else self.priority
                ) for p in patterns
            ]

        params, content = xslt.core.xsltHeader(element, allowedNames=['param'])
        options['definedVars'] = []
        self.params = [Param(i, stylesheet, options) for i in params]
        self.setContent(content, stylesheet, options)

    def instantiateImpl(self, context):
        context.variables = context.toplevelContext.variables.copy()

        for param in self.params:
            param.instantiate(context)

        self.instantiateContent(context)


class Variable(xslt.core.Element):
    name = 'variable'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.qnameProperty(
            element,
            'name',
            namespaces=options['namespaces'],
            required=True
        )
        self.select = xslt.properties.exprProperty(element, 'select')
        self.addDefinition(options)

        if self.select is not None:
            xslt.core.assertEmptyNode(element)
        else:
            self.setContent(element.childNodes, stylesheet, options)

    def addDefinition(self, options):
        if self.name in options['definedVars']:
            raise xslt.exceptions.VariableRedefinition(self.name)
        options['definedVars'].append(self.name)

    def instantiateImpl(self, context):
        if self.select:
            context.parent.variables[self.name] = self.select.find(context)
        else:
            varTree = context.resultDocument.createDocumentFragment()
            varTree.xslt_baseUri = self.baseUri
            context.parent.variables[self.name] = varTree
            context.result = varTree
            self.instantiateContent(context)


class Param(Variable):
    name = 'param'

    def instantiateImpl(self, context):
        if self.name in context.params:
            context.parent.variables[self.name] = context.params[self.name]
        else:
            super(Param, self).instantiateImpl(context)


class WithParam(xslt.core.Element):
    name = 'with-param'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.qnameProperty(
            element,
            'name',
            namespaces=options['namespaces'],
            required=True
        )
        self.select = xslt.properties.exprProperty(element, 'select')

        if self.select is not None:
            xslt.core.assertEmptyNode(element)
        else:
            self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        if self.select is not None:
            context.params[self.name] = self.select.find(context)
        else:
            varTree = context.resultDocument.createDocumentFragment()
            varTree.xslt_baseUri = self.baseUri
            context.params[self.name] = varTree
            context.result = varTree
            self.instantiateContent(context)


class Sort(object):
    name = 'sort'

    def __init__(self, element, stylesheet, options):
        self.select = xslt.properties.exprProperty(
            element,
            'select',
            default='.'
        )
        self.lang = xslt.properties.stringProperty(element, 'lang')
        self.dataType = xslt.properties.stringProperty(
            element,
            'data-type',
            default='text',
            choices=['text', 'number']
        )

        order = xslt.properties.stringProperty(
            element,
            'order',
            default='ascending',
            choices=['ascending', 'descending']
        )
        self.asc = order == 'ascending'

        caseOrder = xslt.properties.stringProperty(
            element,
            'case-order',
            default='upper-first',
            choices=['upper-first', 'lower-first']
        )
        self.upperFirst = caseOrder == 'upper-first'

    def compare(self, context, node1, node2):
        subContext = context.copy()

        subContext.nodeset = [node1]
        v1 = self.select.find(subContext)
        subContext.nodeset = [node2]
        v2 = self.select.find(subContext)

        if self.dataType == 'text':
            v1 = xpath.tools.string(v1, subContext)
            v2 = xpath.tools.string(v2, subContext)
        if self.dataType == 'number':
            v1 = xpath.tools.number(v1, subContext)
            v2 = xpath.tools.number(v2, subContext)

        r = (v1 > v2) - (v1 < v2)
        if not self.asc:
            r = -r
        return r

    @staticmethod
    def sort(context, sortList):
        def compare(a, b):
            for sort in sortList:
                r = sort.compare(context, a, b)
                if r != 0:
                    return r
        if sortList:
            context.nodeset.sort(key=functools.cmp_to_key(compare))


class ApplyTemplates(xslt.core.Element):
    name = 'apply-templates'

    def initImpl(self, element, stylesheet, options):
        self.select = xslt.properties.exprProperty(
            element,
            'select',
            default='node()'
        )
        self.mode = xslt.properties.qnameProperty(
            element,
            'mode',
            namespaces=options['namespaces']
        ) or (None, None)

        self.params = []
        self.sorts = []
        children = xslt.core.xsltChildren(
            element,
            allowedNames=['with-param', 'sort']
        )
        for i in children:
            if i.localName == 'sort':
                self.sorts.append(Sort(i, stylesheet, options))
            if i.localName == 'with-param':
                self.params.append(WithParam(i, stylesheet, options))

    def instantiateImpl(self, context):
        context.nodeset = self.select.findNodeset(context)
        Sort.sort(context, self.sorts)
        context.params = {}
        for i in self.params:
            i.instantiate(context)
        context.stylesheet.applyTemplates(context, self.mode)


class CallTemplate(xslt.core.Element):
    name = 'call-template'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.qnameProperty(
            element,
            'name',
            namespaces=options['namespaces'],
            required=True
        )
        children = xslt.core.xsltChildren(element, allowedNames=['with-param'])
        self.params = [WithParam(i, stylesheet, options) for i in children]

    def instantiateImpl(self, context):
        context.params = {}
        for i in self.params:
            i.instantiate(context)
        context.stylesheet.callTemplate(context, self.name)


class ForEach(xslt.core.Element):
    name = 'for-each'

    def initImpl(self, element, stylesheet, options):
        self.select = xslt.properties.exprProperty(
            element,
            'select',
            required=True
        )
        sorts, content = xslt.core.xsltHeader(element, allowedNames=['sort'])
        self.sorts = [Sort(i, stylesheet, options) for i in sorts]
        self.setContent(content, stylesheet, options)

    def instantiateImpl(self, context):
        context.nodeset = self.select.findNodeset(context)
        context.cause = (None, None)
        Sort.sort(context, self.sorts)
        for node in context:
            self.instantiateContent(context)


class Comment(xslt.core.Element):
    name = 'comment'

    def initImpl(self, element, stylesheet, options):
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        comment = context.resultDocument.createComment(text)
        context.pushResult(comment)
        context.result = comment
        self.instantiateContent(context)


class Copy(xslt.core.Element):
    name = 'copy'

    def initImpl(self, element, stylesheet, options):
        self.useSets = xslt.properties.qnameListProperty(
            element,
            'use-attribute-sets',
            namespaces=options['namespaces'],
            default='',
            resolveDefault=False
        )
        self.setContent(element.childNodes, stylesheet, options)
        self.local_options = options

    def instantiateImpl(self, context):
        r = context.resultDocument.importNode(context.node, False)
        if r.nodeType == xml.dom.Node.ELEMENT_NODE:
            # don't copy attrs except xmlns
            for i in reversed(range(r.attributes.length)):
                attr = r.attributes.item(i)
                if attr.namespaceURI == xml.dom.XMLNS_NAMESPACE:
                    if attr.value in self.local_options['excludeResultNS']:
                        r.removeAttributeNode(attr)
                if attr.namespaceURI != xml.dom.XMLNS_NAMESPACE:
                    r.removeAttributeNode(attr)

        context.pushResult(r)
        context.result = r

        for s in self.useSets:
            context.stylesheet.instantiateAttributeSet(context, s)


class CopyOf(xslt.core.Element):
    name = 'copy-of'

    def initImpl(self, element, stylesheet, options):
        self.select = xslt.properties.exprProperty(
            element,
            'select',
            required=True
        )
        xslt.core.assertEmptyNode(element)

    def instantiateImpl(self, context):
        value = self.select.find(context)

        if not xpath.tools.nodesetp(value):
            value = xpath.expr.string(value)

        context.pushResult(value)


class ValueOf(xslt.core.Element):
    name = 'value-of'

    def initImpl(self, element, stylesheet, options):
        self.select = xslt.properties.exprProperty(
            element,
            'select',
            required=True
        )
        self.disableOutputExcaping = xslt.properties.boolProperty(
            element,
            'disable-output-escaping'
        )

    def instantiateImpl(self, context):
        value = self.select.findString(context)
        text = context.resultDocument.createTextNode(value)
        text.xslt_disableOutputExcaping = self.disableOutputExcaping
        context.pushResult(text)


class ApplyImports(xslt.core.Element):
    name = 'apply-imports'

    def initImpl(self, element, stylesheet, options):
        xslt.core.assertEmptyNode(element)

    def instantiateImpl(self, context):
        context.stylesheet.applyImports(context)


class Number(xslt.core.Element):
    name = 'number'

    def initImpl(self, element, stylesheet, options):
        pass

    def instantiateImpl(self, context):
        pass


class Choose(xslt.core.Element):
    name = 'choose'

    def initImpl(self, element, stylesheet, options):
        whens, tail = xslt.core.xsltHeader(element, ['when'])

        otherwise = xslt.core.xsltChildren(tail, ['otherwise'])
        if len(otherwise) == 0:
            otherwise = None
        elif len(otherwise) == 1:
            otherwise = otherwise[0]
        else:
            raise xslt.exceptions.UnexpectedNode(otherwise[1])

        self.whens = [When(when, stylesheet, options) for when in whens]
        if otherwise:
            self.otherwise = xslt.core.TemplateContent(
                otherwise.childNodes,
                stylesheet,
                options
            )

    def instantiateImpl(self, context):
        for when in self.whens:
            if when.test(context):
                when.instantiate(context)
                return

        if self.otherwise:
            self.otherwise.instantiate(context)


class When(xslt.core.Element):
    name = 'when'

    def initImpl(self, element, stylesheet, options):
        self.testExpr = xslt.properties.exprProperty(
            element,
            'test',
            required=True
        )
        self.setContent(element.childNodes, stylesheet, options)

    def test(self, context):
        return self.testExpr.findBoolean(context)

    def instantiateImpl(self, context):
        self.instantiateContent(context)


class If(xslt.core.Element):
    name = 'if'

    def initImpl(self, element, stylesheet, options):
        self.test = xslt.properties.exprProperty(
            element,
            'test',
            required=True
        )
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        r = self.test.findBoolean(context)
        if r:
            self.instantiateContent(context)


class Text(xslt.core.Element):
    name = 'text'

    def initImpl(self, element, stylesheet, options):
        self.disableOutputExcaping = xslt.properties.boolProperty(
            element,
            'disable-output-escaping'
        )
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        r = context.resultDocument.createTextNode('')
        r.xslt_disableOutputExcaping = self.disableOutputExcaping
        context.pushResult(r)
        context.result = r
        self.instantiateContent(context)


class Message(xslt.core.Element):
    name = 'message'

    def initImpl(self, element, stylesheet, options):
        self.terminate = xslt.properties.boolProperty(
            element,
            'terminate',
            default=False
        )
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        context.result = StringIO()
        self.instantiateContent(context)
        context.toplevelContext.messages.append(context.result.getvalue())
        if self.terminate:
            raise xslt.exceptions.Terminate(context.result.getvalue())


class Fallback(xslt.core.Element):
    name = 'fallback'

    def initImpl(self, element, stylesheet, options):
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        if context.fallback:
            self.instantiateContent(context)


class ProcessingInstruction(xslt.core.Element):
    name = 'processing-instruction'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.stringProperty(element, 'name')
        self.setContent(element.childNodes, stylesheet, options)
        # TODO: check name is NCName and PITarget

    def instantiateImpl(self, context):
        context.result = StringIO()
        self.instantiateContent(context)
        pi = context.resultDocument.createProcessingInstruction(
            self.name.value(context),
            context.result.getvalue()
        )
        context.pushResult(pi)


class ElementTemplate(xslt.core.Element):
    name = 'element'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.attributeTemplateProperty(
            element,
            'name',
            required=True
        )
        self.namespace = xslt.properties.attributeTemplateProperty(
            element,
            'namespace'
        )
        self.useSets = xslt.properties.qnameListProperty(
            element,
            'use-attribute-sets',
            namespaces=options['namespaces'],
            default='',
            resolveDefault=False
        )
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        name = xslt.properties.parseQName(self.name.value(context))
        if self.namespace is None:
            namespace = xslt.properties.resolveQName(
                name,
                namespaces=context.namespaces,
                resolveDefault=True
            )[0]
        else:
            namespace = self.namespace.value(context)
            if namespace == '':
                namespace = None

        e = context.resultDocument.createElementNS(
            namespace,
            xslt.tools.formatQName(name)
        )
        context.pushResult(e)
        context.result = e

        for attrSet in self.useSets:
            context.stylesheet.instantiateAttributeSet(context, attrSet)

        self.instantiateContent(context)


class Attribute(xslt.core.Element):
    name = 'attribute'

    def initImpl(self, element, stylesheet, options):
        self.name = xslt.properties.attributeTemplateProperty(
            element,
            'name',
            required=True
        )
        self.namespace = xslt.properties.attributeTemplateProperty(
            element,
            'namespace'
        )
        self.setContent(element.childNodes, stylesheet, options)

    def instantiateImpl(self, context):
        name = xslt.properties.parseQName(self.name.value(context))
        if self.namespace is None:
            namespace = xslt.properties.resolveQName(
                name,
                namespaces=context.namespaces,
                resolveDefault=True
            )[0]
        else:
            namespace = self.namespace.value(context)
            if namespace == '':
                namespace = None

        e = context.resultDocument.createAttribute(
            namespace,
            xslt.tools.formatQName(name)
        )
        context.pushResult(e)
        context.result = e
        self.instantiateContent(context)
