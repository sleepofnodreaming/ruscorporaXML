﻿import codecs

def count_target_collocations(tree):
    """ count the sequences of target words."""
    targetElements = tree.xpath(u'/page/documents/document/snippet//word[@target]')
    snippetToWordDic = {}
    for word in targetElements:
        snippetNumber = word.getparent().attrib['sid']
        if snippetNumber not in snippetToWordDic:
            snippetToWordDic[snippetNumber] = []
        snippetToWordDic[snippetNumber].append(word)
    seqFD = {}
    for seq in snippetToWordDic.values(): # snippet numbers do not matter
        temp = [u'' for i in range(len(seq))]

        for word in seq:
            wordNum = int(word.attrib['queryPosition'])

            temp[wordNum] = word.attrib['text']
        collocLine = u' '.join(temp).lower()
        if collocLine not in seqFD:
            seqFD[collocLine] = 1
        else:
            seqFD[collocLine] += 1
    return seqFD


def form_snippet_to_words_dic(lexToWordDic): # todo: now this func does nothing. Fix it.
    # Сложно поддающаяся описанию штука, делающая словарь со сниппетами
    # в качестве ключей и с парами (номер_позиции_в_запросе, данные_из_входного_словаря)
    # в качестве значений.
    snippetToWordsDic = {}
    for w in lexToWordDic:
        snippet = w.getparent().attrib['sid']
        lexemeInfo = int(w.attrib['queryPosition']), lexToWordDic[w] # first element is a query position, second one is a lexeme
        if snippet not in snippetToWordsDic:
            snippetToWordsDic[snippet] = []
        snippetToWordsDic[snippet].append(lexemeInfo)
    return snippetToWordsDic


def lexfd(snippetToWordsDic):
    lexemeFD = {}
    for l in snippetToWordsDic.values():
        temp = [u'' for i in range(len(l))]
        for w in l:
            temp[w[0]] = w[1]
        lexSeq = u' '.join(temp)
        if lexSeq not in lexemeFD:
            lexemeFD[lexSeq] = 1
        else:
            lexemeFD[lexSeq] += 1
    return lexemeFD


def count_lemmas(tree):
    """ Draw the statistics of lemmas in the word combinations targeted """
    targetElements = tree.xpath(u'/page/documents/document/snippet//word[@target]/ana[@lex]')
    lexToWordDic = {}
    for l in targetElements:
        word = l.getparent()
        lexeme = l.attrib['lex']
        if word not in lexToWordDic:
            lexToWordDic[word] = []
        lexToWordDic[word].append(lexeme)
    lexToWordDic = {i: u'|'.join(sorted(lexToWordDic[i])) for i in lexToWordDic}
    # snippetToWordsDic = {}
    snippetToWordsDic = form_snippet_to_words_dic(lexToWordDic)
    return lexfd(snippetToWordsDic)


def count_pos(tree):
     """ Form the dic consisting of pos chains as keys and their frequencies as values. """
     targetElements = tree.xpath(u'/page/documents/document/snippet//word[@target]/ana[@gramm]')
     wordToPosDic = {}
     # iterate all the targeted elements and create a dic
     # where the keys are links to word nodes and values are pos lists
     # print targetElements
     for el in targetElements:
         id = el.getparent()
         # print id
         pos = [i.split(u' ')[0] for i in el.attrib['gramm'].split(u'|')]
         if id not in wordToPosDic:
             wordToPosDic[id] = []
         wordToPosDic[id] += pos
     # for k in wordToPosDic:
     #     print k, wordToPosDic
     wordToPosDic = {i: sorted(list(set(wordToPosDic[i]))) for i in wordToPosDic}
     wordToPosDic = {i: u'|'.join(wordToPosDic[i]) for i in wordToPosDic}

     snippetToWordsDic = form_snippet_to_words_dic(wordToPosDic)
     return lexfd(snippetToWordsDic)

def count_full_gr(tree):
     """ Form the dic consisting of full grammar chains as keys and their frequencies as values. """
     targetElements = tree.xpath(u'/page/documents/document/snippet//word[@target]/ana[@gramm]')
     wordToPosDic = {}

     for el in targetElements:
         id = el.getparent()

         pos = [i for i in el.attrib['gramm'].split(u'|')]
         if id not in wordToPosDic:
             wordToPosDic[id] = []
         wordToPosDic[id] += pos

     wordToPosDic = {i: sorted(list(set(wordToPosDic[i]))) for i in wordToPosDic}
     wordToPosDic = {i: u'|'.join(wordToPosDic[i]) for i in wordToPosDic}

     snippetToWordsDic = form_snippet_to_words_dic(wordToPosDic)
     return lexfd(snippetToWordsDic)

def statistics_calculated_to_file(dic, filename):
    """ Write a dic generated by other funcs from this file
    to the file filename."""
    invertedDic = {}
    for i in dic:
        fr = dic[i]
        if fr not in invertedDic:
            invertedDic[fr] = []
        invertedDic[fr].append(i)
    lines = []
    for i in sorted(invertedDic.keys(), key = lambda a: -a): # i'm a genius!
        for word in sorted(invertedDic[i]):
            line = word + u'\t' + unicode(i)
            lines.append(line)
    text = u'\n'.join(lines)
    if text:
        f = codecs.open(filename, 'w', 'utf-8')
        f.write(text)
        f.close()
        return True
    return False

STAT_TYPES = {'lemmas': count_lemmas,
              'wordforms': count_target_collocations,
              'pos': count_pos,
              'gr': count_full_gr}
