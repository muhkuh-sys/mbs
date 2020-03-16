import xpath.exceptions
import xpath.axes


def string_value(node):
    """Compute the string-value of a node."""
    if(
        node.nodeType == node.DOCUMENT_NODE or
        node.nodeType == node.ELEMENT_NODE or
        node.nodeType == node.DOCUMENT_FRAGMENT_NODE
    ):
        s = u''
        for n in xpath.axes.descendant(node):
            if n.nodeType == n.TEXT_NODE:
                s += n.data
        return s

    elif node.nodeType == node.ATTRIBUTE_NODE:
        return node.value

    elif (node.nodeType == node.PROCESSING_INSTRUCTION_NODE or
          node.nodeType == node.COMMENT_NODE or
          node.nodeType == node.TEXT_NODE):
        return node.data


def invoke(name, node, pos, size, context, *args):
    fn = context.functions.get(name)
    if fn is None:
        raise xpath.exceptions.XPathUnknownFunctionError(
            'unknown function "%s()"' % name
        )
    return fn(node, pos, size, context, *args)


def nodeset(v):
    """Convert a value to a nodeset."""
    if not nodesetp(v):
        raise xpath.exceptions.XPathTypeError("value is not a node-set")
    return v


def nodesetp(v):
    """Return true iff 'v' is a node-set."""
    if isinstance(v, list):
        return True


def stringp(v):
    """Return true if 'v' is a string."""
    return isinstance(v, str)


def string(v, context):
    return invoke('string', None, 1, 1, context, v)


def booleanp(v):
    """Return true iff 'v' is a boolean."""
    return isinstance(v, bool)


def boolean(v, context):
    return invoke('boolean', None, 1, 1, context, v)


def numberp(v):
    """Return true iff 'v' is a number."""
    return (not(isinstance(v, bool)) and
            (isinstance(v, int) or isinstance(v, float)))


def number(v, context):
    return invoke('number', None, 1, 1, context, v)
