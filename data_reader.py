
import codecs
import json
import re
import os

from copy import deepcopy


class QueryParsingError(Exception):
    """ This is an exception to use in the RawQueryParser class when
    the method requiring the valid last question is caled without a check. """
    def __init__(self, value):
        self.val = value

    def __str__(self):
        if self.val is None:
            return 'No query was parsed.'
        return 'Errors in lines: %s' % u', '.join([str(i) for i in self.val])


class Defaults(object):
    """ The class contains settings read from permissions.json file,
    along with the url base and a set of parameters hardcored for each query.

    """
    __text = codecs.open('permissions.json', 'r', 'utf-8-sig').read()
    __permissions = json.loads(__text)

    corpora_main_info = __permissions['list_of_acceptable_parameters_in_every_corpora']
    acceptable_lex_param = __permissions['possible_lexeme_parameters']
    acceptable_dist_param = __permissions['possible_distance_parameters']
    outer_to_inner_flag_notation = __permissions['outer_to_inner']
    wordform_defaults = __permissions['wordform_defaults']
    homonymy_option_available = __permissions['homonymy_hadled']

    URL = u'http://search.ruscorpora.ru/dump.xml?'

    # This is a set of parameters hardcored in every URL.
    # I could not remove them as I DO NOT know why they are there (I had no docs, really).
    hardcored = {
        "env": "alpha",
        "mycorp": "",
        "mysent": "",
        "mysize": "",
        "mysentsize": "",
        "mydocsize": "",
        "spd": "",
        "text": "lexgramm",
        "mode": "main",
        "sort": "gr_tagging",
        "lang": "ru",
        "nodia": "1",
    }


class RawQueryParser(object):
    """ The class handling queries in a raw format. """

    # the basic query part
    _queryMain = Defaults.URL + u'&'.join([u'%s=%s' % (i, Defaults.hardcored[i]) for i in Defaults.hardcored]) + '&'

    def __init__(self):
        # A regex where the first group is a list of corpora.
        corporaListRegexText = u'corpora\\s*:\\s*(.*)$'
        self.corporaListRegex = re.compile(corporaListRegexText, flags = re.U|re.I)

        # The first group is a name of parameter,
        # and the second one is a parameter itself.
        innerLineWF = u'|'.join([u'(?:%s)' % i for i in Defaults.acceptable_lex_param])
        innerLineDist = u'|'.join([u'(?:%s)' % i for i in Defaults.acceptable_dist_param])
        paramListRegexWF = u'(%s)\\s*:\\s*\\{([^\\}]*)\\}\\s*' % innerLineWF
        paramListRegexDist = u'(%s)\\s*:\\s*([\\d]+)\\s*' % innerLineDist

        self.paramListRegexes = {
                        'word': re.compile(paramListRegexWF, flags = re.U|re.I),
                        'dist': re.compile(paramListRegexDist, flags = re.U|re.I)
                        }

        self.paramListTests = {'word': Defaults.acceptable_lex_param,
                               'dist': Defaults.acceptable_dist_param}
        self.lastUnread = None
        self.lastQuery = None
        self.lastCorpora = None

    @staticmethod
    def _parse_corpora_list(string):
        """ Split the list of corpora by commas. """
        string = string.strip().replace(u' ', u'')
        return string.split(u',')

    @staticmethod
    def _filter_params(paramsFromFindall):
        """ Delete empty search parameters. """
        return [i for i in paramsFromFindall if i[1]]

    def _check_param_validity(self, parameters, currentRegexKey):
        """
        Check if the input has appropriate parameter keys. WARNING: vals are not checked.
        Possible param keys are listed in permissions.json:
            word: possible_lexeme_parameters
            dist: possible_distance_parameters
        :param parameters: a list of pairs: (parameter name, parameter value).
        :param currentRegexKey: a str 'word' or 'dist'. If it is 'word', a paramset for a word specified is checked;
        otherwise, distance keys are checked.
        :return: A boolean value showing whether the parameter keys are correct.

        """

        for pair in parameters:
            if pair[0] not in self.paramListTests[currentRegexKey]:
                return False
        return True

    def read_corpora_query(self, readable):
        """
        Read the data from something can provide lines in the cfg file format.
        :param readable: a request as readable (should be open, func is not responsible for the resource;
        in fact, iterable is enough).
        :return: nothing, but updates a few object attributes:
            self.lastUnread (a list of incorrect query lines, starting with 1)
            self.lastQuery
            self.lastCorpora

        """
        unreadable, requestParam, corpora = [], [], []
        lineCounter = 1 # it starts with 1 because it is more human-readable
        currentRegexKey = 'word'

        for line in readable:
            if isinstance(line, str):
                line = line.decode('utf-8')
            if lineCounter == 1:
                m = self.corporaListRegex.search(line)
                if m is None: # corpora list not found.
                    unreadable.append(lineCounter)
                else:
                    corpora = RawQueryParser._parse_corpora_list(m.group(1))
            else:

                params = self.paramListRegexes[currentRegexKey].findall(line)
                params = RawQueryParser._filter_params(params)
                if not params or not self._check_param_validity(params, currentRegexKey):
                    unreadable.append(lineCounter)
                else:
                    requestParam.append(params)
                    nextKey = 'dist' if currentRegexKey == 'word' else 'word'
                    currentRegexKey = nextKey

            lineCounter += 1

        self.lastUnread = unreadable
        self.lastQuery = requestParam
        self.lastCorpora = corpora
        # print self.lastQuery
        # print self.lastCorpora
        # print self.get_url_for(self.get_query_dic(), Defaults.hardcored)


    def last_is_appropriate(self):
        """ Check if the last query parsed is correct.

        """
        if self.lastUnread:
            return False
        return True

    def get_query_dic(self):
        """ Convert a query to a dictionary.
        :return: A dict {parameter: [values]}. All The values except for semantic issies should be one-item length.
        If the last query is invalid, the return is None.

        """
        if self.last_is_appropriate():
            queryDic = {}
            for lineNum in xrange(len(self.lastQuery)):
                line = self.lastQuery[lineNum]
                index = unicode(lineNum / 2 + 1)
                if lineNum % 2 == 0: # numLine is even. The line contains the info about a word.
                    for pBaseName, pVal in line:
                        pRealName = Defaults.outer_to_inner_flag_notation[pBaseName] + index
                        if pBaseName != u'semflags':
                            # pRealName = Defaults.outer_to_inner_flag_notation[pBaseName] + index
                            if pRealName not in queryDic:
                                queryDic[pRealName] = []
                            queryDic[pRealName].append(pVal)
                        else:
                            # todo check semflags processing here
                            modeNums = pVal.replace(u' ', u'').split(u',')
                            queryDic[pRealName] = [u'sem'+i if i != u'1' else u'sem' for i in modeNums]
                    for key in Defaults.wordform_defaults:
                        if key+index not in queryDic:
                            queryDic[key+index] = [Defaults.wordform_defaults[key]]
                else:
                    for pBaseName, pVal in line:
                        tmp = u'min' if pBaseName == 'distfrom' else u'max'
                        pRealName = tmp + index
                        if pRealName not in queryDic:
                            queryDic[pRealName] = []
                            queryDic[pRealName].append(pVal)

            return queryDic

    @staticmethod
    def get_url_for(query, baseData):
        allData = [(key, baseData[key]) for key in baseData]
        for key in query:
            for value in query[key]:
                allData.append((key, value, ))
        return Defaults.URL + u'&'.join([u'%s=%s' % pair for pair in allData])

    # @staticmethod
    # def _convert_semantic_flags(arrayOfPairs, number):
    #     """ Convert the line containing semantic flags to a normal part of query."""
    #     # todo: rewrite this shit.
    #     for el in range(len(arrayOfPairs)):
    #         if arrayOfPairs[el][0] == u'semflags':
    #             temp = arrayOfPairs[el][1].replace(u' ', u'')
    #             temp = temp.replace(u',', u'&sem-mod%s=' % unicode(number))
    #             newPair = arrayOfPairs[el][0], temp
    #             arrayOfPairs[el] = newPair
    #
    # @staticmethod
    # def _distance_qpart(distLine, number):
    #     """ Convert a line containing distance info to the part of a query. """
    #     numText = unicode(number)
    #     l = []
    #     for i in distLine:
    #         if i[0] == 'distfrom':
    #             l.append(u'min%s=%s' % (numText, i[1]))
    #         elif i[0] == 'distto':
    #             l.append(u'max%s=%s' % (numText, i[1]))
    #     return u'&'.join(l)
    #
    # @staticmethod
    # def _one_word_query(wordLine, number):
    #     """ Put together the info on one word, given a line and a number of word in a query."""
    #     numText = unicode(number)
    #     # form the part of line where the values are defined
    #     newWordLine = [Defaults.outer_to_inner_flag_notation[paramName] + numText + u'=' + paramVal for paramName, paramVal in wordLine]
    #     existingQParts = [Defaults.outer_to_inner_flag_notation[paramName] for paramName, paramVal in wordLine]
    #     # adding the defaults
    #     for key in Defaults.wordform_defaults:
    #         if key not in existingQParts:
    #             temp = key + numText + u'=' + Defaults.wordform_defaults[key]
    #             newWordLine.append(temp)
    #     return u'&'.join(newWordLine)
    #
    # def _compile_url_template(self):
    #     """ Compile a url from a query parsed, if possible. Otherwise, raise QueryParsingError. """
    #
    #     if not self.last_is_appropriate():
    #         raise QueryParsingError(self.lastUnread)
    #
    #     request = deepcopy(self.lastQuery) # self.convert_semantic_flags() spoils the data, so work with a copy.
    #
    #     queryParts = []
    #     for numLine in range(len(request)):
    #         if numLine % 2 == 0: # numLine is even. The line contains the info about a word.
    #             self._convert_semantic_flags(request[numLine], numLine / 2 + 1)
    #             part = self._one_word_query(request[numLine], numLine / 2 + 1)
    #         else:
    #             part = self._distance_qpart(request[numLine], numLine / 2 + 1)
    #         queryParts.append(part)
    #     # print self._queryMain + u'&'.join(queryParts)
    #     return self._queryMain + u'&'.join(queryParts)

    def get_subcorpora_query_iterator(self, **kwargs):
        """ If the last query processed is valid, return a function to generate pairs of names and URLs.
        Otherwise, QueryParsingError will be raised.
        :return: a function without args returning a generator providing pairs (corpora name, path to the first dump page).

        """
        def func():
            base = deepcopy(Defaults.hardcored)
            base.update(kwargs)
            query = self.get_query_dic()
            for corpName in self.lastCorpora:
                base["mode"] = corpName
                url = self.get_url_for(query, base)
                yield corpName, url
            # urlTemplate = self._compile_url_template()
            # corpList = self.lastCorpora[:]
            # for corpus in corpList:
            #     yield corpus, urlTemplate % corpus
        return func

    def get_subcorpora_query_list(self, **kwargs):
        """ If the last query processed is valid, return a list of pairs of names and URLs.
        Otherwise, QueryParsingError will be raised.
        :return: list of pairs (corpora name, path to the first dump page).

        """
        seq_gen = self.get_subcorpora_query_iterator(**kwargs)
        return list(seq_gen())

    def from_file(self, path):
        """ Given a path to a file, parse it and return a sequence of subrequests (see RawQueryParser.get_subcorpora_query_list()).
        If an error occured while parsing, raise QueryParsingError. If there is no file, raise IOError. """
        if os.path.exists(path) and os.path.isfile(path):
            with codecs.open(path, 'r', 'utf-8-sig') as f:
                self.read_corpora_query(f)
                if not self.last_is_appropriate():
                    raise QueryParsingError(self.lastUnread)
                return self.get_subcorpora_query_list()
        else:
            raise IOError()

