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
    _query_main = Defaults.URL + u'&'.join([u'%s=%s' % (i, Defaults.hardcored[i]) for i in Defaults.hardcored]) + '&'

    def __init__(self):
        # A regex where the first group is a list of corpora.
        corpora_list_regex_text = u'corpora\\s*:\\s*(.*)$'
        self.corpora_list_regex = re.compile(corpora_list_regex_text, flags=re.U | re.I)

        # The first group is a name of parameter,
        # and the second one is a parameter itself.
        inner_line_wf = u'|'.join([u'(?:%s)' % i for i in Defaults.acceptable_lex_param])
        inner_line_dist = u'|'.join([u'(?:%s)' % i for i in Defaults.acceptable_dist_param])
        param_list_regexwf = u'(%s)\\s*:\\s*\\{([^\\}]*)\\}\\s*' % inner_line_wf
        param_list_regex_dist = u'(%s)\\s*:\\s*([\\d]+)\\s*' % inner_line_dist

        self.param_list_regexes = {
            'word': re.compile(param_list_regexwf, flags=re.U | re.I),
            'dist': re.compile(param_list_regex_dist, flags=re.U | re.I)
        }

        self.paramListTests = {
            'word': Defaults.acceptable_lex_param,
            'dist': Defaults.acceptable_dist_param
        }
        self.last_unread = None
        self.last_query = None
        self.last_corpora = None

    def _check_param_validity(self, parameters, current_regex_key):
        """
        Check if the input has appropriate parameter keys. WARNING: vals are not checked.
        Possible param keys are listed in permissions.json:
            word: possible_lexeme_parameters
            dist: possible_distance_parameters
        :param parameters: a list of pairs: (parameter name, parameter value).
        :param current_regex_key: a str 'word' or 'dist'. If it is 'word', a paramset for a word specified is checked;
        otherwise, distance keys are checked.
        :return: A boolean value showing whether the parameter keys are correct.

        """

        for pair in parameters:
            if pair[0] not in self.paramListTests[current_regex_key]:
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
        unreadable, request_param, corpora = [], [], []
        line_counter = 1  # it starts with 1 because it is more human-readable
        current_regex_key = 'word'

        for line in readable:
            if isinstance(line, str):
                line = line.decode('utf-8')
            if line_counter == 1:
                m = self.corpora_list_regex.search(line)
                if m is None:  # corpora list not found.
                    unreadable.append(line_counter)
                else:
                    corpora = m.group(1).strip().replace(u' ', u'').split(u',')
            else:
                params = self.param_list_regexes[current_regex_key].findall(line)
                params = [i for i in params if i[1]]  # Delete empty params.
                if not params or not self._check_param_validity(params, current_regex_key):
                    unreadable.append(line_counter)
                else:
                    request_param.append(params)
                    nextKey = 'dist' if current_regex_key == 'word' else 'word'
                    current_regex_key = nextKey

            line_counter += 1

        self.last_unread = unreadable
        self.last_query = request_param
        self.last_corpora = corpora

    def last_is_appropriate(self):
        """
        Check if the last query parsed is correct.
        :return: a boolean.

        """
        if self.last_unread:
            return False
        return True

    def get_query_dic(self):
        """
        Convert the last query to a dictionary.
        :return: A dict {parameter: [values]}. All the values except for semantic issies should be one-item length.
        If the last query is invalid, the return is None.

        """
        if self.last_is_appropriate():
            query_dic = {}
            for line_num in xrange(len(self.last_query)):
                line = self.last_query[line_num]
                index = unicode(line_num / 2 + 1)
                if line_num % 2 == 0:  # numLine is even. The line contains the info about a word.
                    for param_base_name, param_val in line:
                        param_real_name = Defaults.outer_to_inner_flag_notation[param_base_name] + index
                        if param_base_name != u'semflags':
                            # param_real_name = Defaults.outer_to_inner_flag_notation[param_base_name] + index
                            if param_real_name not in query_dic:
                                query_dic[param_real_name] = []
                            query_dic[param_real_name].append(param_val)
                        else:
                            # todo check semflags processing here
                            mode_nums = param_val.replace(u' ', u'').split(u',')
                            query_dic[param_real_name] = [u'sem' + i if i != u'1' else u'sem' for i in mode_nums]
                    for key in Defaults.wordform_defaults:
                        if key + index not in query_dic:
                            query_dic[key + index] = [Defaults.wordform_defaults[key]]
                else:
                    for param_base_name, param_val in line:
                        distance_identifier = u'min' if param_base_name == 'distfrom' else u'max'
                        param_real_name = distance_identifier + index
                        if param_real_name not in query_dic:
                            query_dic[param_real_name] = []
                            query_dic[param_real_name].append(param_val)

            return query_dic

    @staticmethod
    def get_url_for(query, base_data):
        all_data = [(key, base_data[key]) for key in base_data]
        for key in query:
            for value in query[key]:
                all_data.append((key, value,))
        return Defaults.URL + u'&'.join([u'%s=%s' % pair for pair in all_data])

    def get_subcorpora_query_iterator(self, **kwargs):
        """ If the last query processed is valid, return a function to generate pairs of names and URLs.
        Otherwise, QueryParsingError will be raised.
        :return: a function without args returning a generator providing pairs (corpora name, path to the first dump page).

        """

        def func():
            base = deepcopy(Defaults.hardcored)
            base.update(kwargs)
            query = self.get_query_dic()
            for corp_name in self.last_corpora:
                base["mode"] = corp_name
                url = self.get_url_for(query, base)
                yield corp_name, url

        return func

    def get_subcorpora_query_list(self, **kwargs):
        """
        If the last query processed is valid, return a list of pairs of names and URLs.
        Otherwise, QueryParsingError will be raised.
        :return: list of pairs (corpora name, path to the first dump page).

        """
        seq_gen = self.get_subcorpora_query_iterator(**kwargs)
        return list(seq_gen())

    def from_file(self, path):
        """
        Parse a file to a sequence of resuests.
        If an error occured while parsing, raise QueryParsingError. If there is no file, raise IOError.
        :param path: a path to the file.
        :return: a sequence of subrequests (see RawQueryParser.get_subcorpora_query_list()).

        """
        if os.path.exists(path) and os.path.isfile(path):
            with codecs.open(path, 'r', 'utf-8-sig') as f:
                self.read_corpora_query(f)
                if not self.last_is_appropriate():
                    raise QueryParsingError(self.last_unread)
                return self.get_subcorpora_query_list()
        else:
            raise IOError()
