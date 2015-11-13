

class _XPathModifierQueries(object):
    # analyses = u'/page/documents/document/snippet/word/ana'
    # snippets = u'/page/documents/document/snippet'
    # words = u'/page/documents/document/snippet/word'

    analyses = u'/page/documents/document/snippet//word/ana'
    snippets = u'/page/documents/document//snippet'
    words = u'/page/documents/document/snippet//word'


def delete_irrelevant_features(tree, listOfinfoTypes): # OK.
    """ Remove metainfo tags not matching the categories mentioned in
    listOfinfoTypes from a tree. Return the cleared tree. """
    for el in tree.xpath(_XPathModifierQueries.analyses):
        for subEl in el:
            if 'name' in subEl.attrib and subEl.attrib['name'] in listOfinfoTypes:
                el.remove(subEl)
        if not len(el):
            el.getparent().remove(el)
    return tree


def get_targeted_range(snippet):
    """ Find the numbers of the leftmost and the rigthmost
    target words in the snippet. 'word' tags only mentioned; 'text' tags are omitted. """
    counter = 0
    firstTargetNode = None
    lastTargetNode = None
    for word in snippet:
        if word.tag == 'word':
            if 'queryPosition' in word.attrib:
                if firstTargetNode == None:
                    firstTargetNode = counter
                lastTargetNode = counter
            counter += 1
    if firstTargetNode is not None:
        return firstTargetNode, lastTargetNode
    return None


def apply_context_range(tree, leftNum, rightNum):
    """ Delete all the ana tags which are not in the defined interval
    around the target elements. """
    for snippet in tree.xpath(_XPathModifierQueries.snippets):

        firstTargetNode = None
        lastTargetNode = None

        targetRange = get_targeted_range(snippet)

        if targetRange is not None:
            firstTargetNode, lastTargetNode = targetRange

        if firstTargetNode is not None:
            firstTargetNode -= leftNum # начиная с этого номера (включительно?) надо оставлять теги
            lastTargetNode += rightNum # всё, что больше этого числа, тоже с тегами
        counter = 0
        for word in snippet:
            if word.tag == 'word':
                if firstTargetNode is None or \
                   counter < firstTargetNode or \
                   counter > lastTargetNode:
                    for analysis in word:
                        word.remove(analysis)

                counter += 1
    return tree


def delete_complete_trash(tree):
    """ Clear the tree from senseless tags. Return the tree."""
    for word in tree.xpath(_XPathModifierQueries.words):
        if 'code' in word.attrib:
            word.attrib.pop('code')
    return tree


def arrange_tree_tags(tree, leftNum, rightNum):
    """ Apply all the clearing functions to a tree."""
    delete_complete_trash(tree)
    apply_context_range(tree, leftNum, rightNum)
#    delete_irrelevant_features(tree, features)


def compress_tree(elTree):
    """ Change atom tags to the normal ones. """
    nodesToCompress = elTree.xpath(_XPathModifierQueries.analyses)
    for node in nodesToCompress: # это теги ana
        for el in node: # el tag. contains name, value should be added
            anaValue = el.attrib['name']
            grParts = []
            for elGr in el:
                groupText = []
                for elAtom in elGr:
                    groupText.append(elAtom.text)
                grParts.append(u' '.join(groupText))
            valText = u'|'.join(grParts)
            node.attrib[anaValue] = valText
        for anaChild in node:
            node.remove(anaChild)


