import time, codecs, os
from lxml import etree
from StringIO import StringIO
from copy import deepcopy
from data_reader import Defaults
from tree_modifiers import delete_irrelevant_features, compress_tree, arrange_tree_tags
from xml_statistics import STAT_TYPES, statistics_calculated_to_file
import random
import re

TIME_INTERVAL = 0.1
QUERY_LIMIT = 1000

class _XPathSnippetQueries(object):
    """ In fact, this is just a place to encapsulate xpath queries.

    """
    request = u'.//query'
    docs = u'.//body/result/document'
    statistics = u'.//body/result'
    format = u'.//body/request/format'
    snippets = u'.//body/result/document/snippet'
    docattrib = u'.//attributes'


class PageDownloadError(Exception):
    """ This should be raised if there's something wrong in the downloader.

    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return 'Something went wrong while downloading a page: %s' % self.value


class _SnippetExtensionError(Exception):
    """ This should be raised if it's impossible to parse snippet.

    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return 'Cannot process URL: %s' % self.value


class SnippetParsingError(_SnippetExtensionError):
    def __str__(self):
        return 'Cannot process URL: %s. A number of contexts is more than one' % self.value


class SnippetDownloadingError(_SnippetExtensionError):
    def __str__(self):
        return 'Cannot process URL: %s. It is impossible to download the data.' % self.value


class Downloader(object):

    def __init__(self):
        self.callCounter = 0

    def download_page(self, currentUrl):
        """ Download a page located to the currentUrl and return it as a string. """
        try:
            parsedXml = etree.parse(currentUrl)
            return parsedXml
        except IOError:
            raise PageDownloadError(currentUrl)

    def __call__(self, *args, **kwargs):
        page = self.download_page(*args)
        self.callCounter += 1
        return page


download_page = Downloader()


def get_filename_by_url(url):
    """ Given a url, find some relevant parts and return a name of a file (without an extension). """
    namingRegex = re.compile(ur'(?:(?:lex\d)|(?:gramm\d+)|(?:mode))=([^&]+)', flags=re.U|re.I)
    readableParts = namingRegex.findall(url)
    cTime = time.strftime('%Y.%m.%d %H.%M')
    qDscr = u''
    if readableParts:
        qDscr = u' - %s' % u'_'.join(readableParts)
    return u'%s%s' % (cTime, qDscr)




def extract_snippet_by_link(link): # OK
    """
    Get a link to a snippet in full and extract a snippet subtree.
    If there's more than one snippet per page, sth went wrong: raise a SnippetExtentionError exception.
    If there is a downloader error, raise SnippetExtentionError, too.
    Otherwise, return the snippet subtree. This func is used to extend contexts.
    """
    try:
        tree = download_page(link) # here may be PageDownloadError

        snippets = tree.getroot().xpath(_XPathSnippetQueries.snippets)
        if len(snippets) == 1:
            return snippets[0]
        else:
            raise SnippetParsingError(link)
    except:
        raise SnippetDownloadingError(link)


def estimate_page_number(elTree):
    """ Given a tree representing the first page of the output,
    calculate the number of pages in the output. """
    if elTree:
        docNum = elTree.getroot().xpath(_XPathSnippetQueries.statistics)[0].attrib['documents']
        docPerPageNum = elTree.getroot().xpath(_XPathSnippetQueries.format)[0].attrib['documents-per-page']
        docNum, docPerPageNum = int(docNum), int(docPerPageNum)
        if docNum:
            numOfPages = (docNum / docPerPageNum) + 1 # a ceiling.
            return numOfPages
    return 0


def download_all_response_pages(url, exLim, timeInterval):
    """ Download all the pager of an output required.
    :param url: an initial query URL (no page number specified).
    :param exLim: the maximum number of pages to require.
    :param timeInterval: an interval between queries.
    :return: (a list of XMLs, flag is the process was interrupted).

    """

    interrupted = False

    firstPage = download_page(url)

    pageNum = estimate_page_number(firstPage)

    if pageNum == 0:
        return [], interrupted

    outputs = [firstPage]
    if exLim is not None and exLim >= 1 and exLim < pageNum:
        pageNum = exLim

    pageLinks = [url + u'&p=%s' % i for i in range(1, pageNum)]
    for pLink in pageLinks:
        try:
            newPage = download_page(pLink)
            outputs.append(newPage)
            time.sleep(timeInterval)
        except PageDownloadError:
            interrupted = True
            break

    return outputs, interrupted


def modify_url_to_handle_homonymy(url, homonymyIsOK = False):
    """ Change url in order to use a certain subcorpus. """

    if homonymyIsOK == False:
        replacementPart = u'mycorp=%28%28tagging%253A%2522manual%2522%29%29&'
    else:
        replacementPart = u'mycorp=%28%28tagging%253A%2522none%2522%29%29&'
    return url.replace(u'mycorp=&', replacementPart)


def _create_empty_docnode(docNode):
    """ Given an attribute node, create an analogue of its parent, but empty. """
    newDocNode = etree.XML(u'<document></document>')
    for a in docNode.attrib:
        newDocNode.attrib[a] = docNode.attrib[a]
    docAttribute = docNode.xpath(_XPathSnippetQueries.docattrib)
    for i in docAttribute:
        newDocNode.append(i)
    return newDocNode


def _form_document_node(docNode, queryLink, extension_required=True):
    """ Get an 'attribute' node and convert it to the extended version. Return a document node. """
    extensionSuccessful, extensionFailCounter = True, 0
    newDocNode = _create_empty_docnode(docNode)

    docItself = docNode
    docID = docItself.attrib['id']
    for snippet in docItself:

        if extensionFailCounter < 2 and extension_required: # if there were two fails trying to extend, we should stop.

            if snippet.tag == 'snippet':
                sid = snippet.attrib['sid']
                template = u'%s&docid=%s&sid=%s' % (queryLink, docID, sid)

                try:

                    fullSnippet = extract_snippet_by_link(template)
                    newDocNode.append(fullSnippet)

                except SnippetParsingError: # this is just a broken link
                    newDocNode.append(snippet)
                    extensionSuccessful = False

                except SnippetDownloadingError: # this may be an Internet connection problem
                    newDocNode.append(snippet)
                    extensionFailCounter += 1
                    extensionSuccessful = False

        else:
            newDocNode.append(snippet)
    return newDocNode, extensionSuccessful, extensionFailCounter


def _add_output_description(src, dst):
    """ Given a source tree and an output tree, ans a corpora name,
    modify an output node to contain all the info. Return a node to add snippets. """
    root = dst.getroot()
    queryText = src.getroot().xpath(_XPathSnippetQueries.request)
            # And put it into the new tree, if needed.
    if queryText and not root.xpath(_XPathSnippetQueries.request):
        root.append(deepcopy(queryText[0]))
    # If there's a new corpora, create a tag in the hierarchy.
#    nodeForDocs = etree.XML(u'<documents corpora="%s"></documents>' % corporaName)
    nodeForDocs = etree.XML(u'<documents></documents>')
    root.append(nodeForDocs)
    return nodeForDocs


def compile_output_xml(dumpsInArray, queryLink = None, extension=True):
    """ Put all the document tags from the dumpsInArray list to
    the elementTree. If needed, create a tree. Return the tree.
    If queryLink is not None, extra contexts should be downloaded;
    it should be the initial query link."""

    isextended = True
    newTree = etree.parse(StringIO(u'<page></page>'))

    for dumpPageNum in range(len(dumpsInArray)):
        tempTree = dumpsInArray[dumpPageNum]
        # if there's a start of an array processing, get the query info.
        if dumpPageNum == 0:
            nodeForDocs = _add_output_description(dumpsInArray[dumpPageNum], newTree)
        # Finally, extract all the docs and save them to the new tree.
        if queryLink == None:
            for doc in tempTree.getroot().xpath(_XPathSnippetQueries.docs):
                nodeForDocs.append(doc)
        else:
            extensionSuccessful, extensionFailCounter = True, 0
            for docNode in tempTree.getroot().xpath(_XPathSnippetQueries.docs):
                newDocNode, extensionSuccessful, extensionFailCounter = _form_document_node(docNode, queryLink, extension)
                nodeForDocs.append(newDocNode)
                if not extensionSuccessful:
                    isextended = False
    return newTree, isextended


def specify_dst_path(url, dst, dstIsFile, stat = u''):
    """ If a path is to a directory, create a filename for a new file.
    It is guaranteed that the file does not exist. """
    if not stat:
        initialTemplate = u'%s.xml'
        furtherTemplate = u'%s (%s).xml'
    else:
        initialTemplate = u'%s_' + stat + u'.csv'
        furtherTemplate = u'%s_' + stat +  u' (%s).csv'
    if not dstIsFile:
        filename = get_filename_by_url(url)
        fullFilename = os.path.join(dst, initialTemplate % filename)
        counter = 1
        while os.path.exists(fullFilename):
            fullFilename = os.path.join(dst, furtherTemplate % (filename, counter))
            counter += 1
        return fullFilename
    return dst


def apply_all_statistics_to_tree(statisticsList, tree, dst, srcURL):
    """
    :param statisticsList: a list of statistics to apply to the data,
    :param tree: the data tree,
    :param dst: a dir where the results should be saved.
    :return: a list of names of counts failed.
    """

    fails = []
    if tree:
        for key in statisticsList:
            statistics_calc = STAT_TYPES[key]
            stDic = statistics_calc(tree)
            dstFile = specify_dst_path(srcURL, dst, False, key)
            check = statistics_calculated_to_file(stDic, dstFile)
            if not check:
                fails.append(key)
    return fails


def execute_url_query(fullQuery, dst, settings, dstIsFile, statistics):
    """ execute the query fullQuery and save the results to a path outputFileName,
    using general settings generalSettingDic. No validation required (data should be checked externally).
    Return the tree to count any statistics in the future.
    If the func returns None, we should label that there's nothing found. """

    # This is an irrelevant piece just because of a copypaste.
    listOfFeaturesToDelete = settings['tags_to_delete']
    leftBorder = settings['leftcontext']
    rightBorder = settings['rightcontext']
    numberOfExamples = settings['exlim']
    ipiswhite = settings['whiteip']
    contexts = settings['contexts']

    timeInterval = TIME_INTERVAL
    if ipiswhite:
        timeInterval = 0
    try:
        dumps, interrupted = download_all_response_pages(fullQuery, numberOfExamples, timeInterval) # here may be an exception.
    except:
        return None
    if dumps:
        tree, extensionSuccessful = compile_output_xml(dumps, fullQuery, extension=contexts)
        arrange_tree_tags(tree, leftBorder, rightBorder)
        treeCopy4Stat = deepcopy(tree)
        delete_irrelevant_features(tree, listOfFeaturesToDelete)
        compress_tree(tree)
        compress_tree(treeCopy4Stat)
        text = etree.tostring(tree.getroot(), encoding=unicode, pretty_print = True)
        if dst:
            outputPath = specify_dst_path(fullQuery, dst, dstIsFile)
            f = codecs.open(outputPath, 'w', 'utf-8')
            f.write(text)
            f.close()
        if statistics:
            assert not dstIsFile # this can't be
            apply_all_statistics_to_tree(statistics, treeCopy4Stat, dst, fullQuery)
        return {'tree': treeCopy4Stat, 'interrupted': interrupted, 'extended': extensionSuccessful, 'type': 'atom'}
    return {'tree': None, 'interrupted': False, 'extended': True, 'type': 'atom'}



def execute_query_seq(queryIterable, pathToDirectory, settings, statistics):
    """ Given a sequence of pairs (corporaName, query), execute them and return a dictionary of results. """
    resultDic = {}

    for corpName, query in queryIterable:

        output = execute_url_query(query, pathToDirectory, settings, False, statistics)

        resultDic[corpName] = output
    return resultDic


def execute_query_seq_with_settings(queries, pathToDirectory, settings, statistics):

    homonymy = settings['homonymy_in_main_allowed']
    queriesPostprocessed = []
    for corpName, fullQuery in queries:
        if homonymy == True and corpName in Defaults.homonymy_option_available:
             fullQuery = modify_url_to_handle_homonymy(fullQuery)
        # if settings['rand']:
        #      fullQuery = randomize_output(fullQuery)
        pair = (corpName, fullQuery)
        queriesPostprocessed.append(pair)

    treeDic = execute_query_seq(queriesPostprocessed, pathToDirectory, settings, statistics)

    disconnected = [i for i in treeDic if treeDic[i] == None]
    emptyResponseList = [i for i in treeDic if i not in disconnected and treeDic[i]['tree'] == None]
    valid = {i: treeDic[i]['tree'] for i in treeDic if i not in disconnected}
    interrupted = [i for i in treeDic if treeDic[i] != None and treeDic[i]['interrupted']]
    notExtended = [i for i in treeDic if treeDic[i] != None and not treeDic[i]['extended']]

    completeOutput = {'invalidCorpNames': [],
                      'inappropriateQuery': [],
                      'nothingFound': list(emptyResponseList),
                      'output': valid,
                      'disconnected': disconnected,
                      'interrupted': interrupted,
                      'notExtended': notExtended,
                      'type': 'multiple'}
    return completeOutput
