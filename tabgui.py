# -*- coding: utf-8 -*-

from Tkinter import *
from ttk import Notebook
from tkFileDialog import askdirectory, asksaveasfilename
from tkMessageBox import *
from corpora_data_downloader import *
import urllib

from data_reader import *
from Queue import Queue


class _DialogueLabels(object):
    exit_message = {'title': u'Выход',
                    'message': u'Программа обработала не все ваши задачи. Отменить их и выйти?'}

    input_parsing_error = {'message': u'Найдены ошибки в строках: %s'}

    statistics_output_warning = {'message': u'Все файлы со статистикой будут выгружены в папку %s.'}

    save_query_choice = {'message': u'Выберите файл для сохранения запроса'}
    save_query_error = {'message': u'Не удалось сохранить запрос'}

    save_output_directory_choice = {'message': u'Выберите папку для выгрузки данных'}

    save_output_file_choice = {'message': u'Выберите файл для сохранения выдачи'}

    @classmethod
    def generate_raw_query_error(self, parsedRequest):
        """ Given a query description... """
        text = u', '.join([unicode(i) for i in parsedRequest[0]])
        output = {i: self.input_parsing_error[i] for i in self.input_parsing_error}
        output['message'] = output['message'] % text
        return output

    @classmethod
    def generate_statistics_output_warning(self, path):
        output = {i: self.statistics_output_warning[i] for i in self.statistics_output_warning}
        output['message'] = output['message'] % path
        return output


class _WindowLabels(object):

    window_title = u'Dump Downloader'

    tabs = {'url': u'Ввод URL',
            'file': u'Запрос',
            'st': u'Статистика'}

    context_left_label = {'text': u'Левый контекст:'}
    context_right_label = {'text': u'Правый контекст:'}
    tag_deletion_labels = {'text': u'Удалить теги:'}
    homonymy_allowed_label = {'text': u'Только с разрешенной \nомонимией'}

    output_tags = [(u'Прочие пометки', 'flags'),
                   (u'Грамматика', 'gramm'),
                   (u'Основная семантика', 'sem'),
                   (u'Семантика — прочее', 'sem2'),
                   (u'Словообразование', 'word_formation')]

    cascade_file_label = u'Файл'

    cascade_file_save_query = u"Сохранить описание запроса"


tabs = {'url': u'Ввод URL',
        'file': u'Запрос',
        'st': u'Статистика'}


defaultCfg = 'cfg.txt'
defaultGeneralCfg = 'general.txt'

class CopyPasteText(Text):
    """ A text widget where all the functions concerning
    text processing are provided. """
    def __init__(self, master, **kw):
        Text.__init__(self, master, **kw)
     #   self.bind('<Key>', self.test)
      #  self.bind('<Shift-BackSpace>', self.delete_all)
        # self.bind('<Control-c>', self.copy)
        # self.bind('<Control-x>', self.cut)
        # self.bind('<Control-v>', self.paste)

    # def test(self, event):
    #     print event.keysym
    #
    # def copy(self, event=None):
    #     self.clipboard_clear()
    #     text = self.get("sel.first", "sel.last")
    #     self.clipboard_append(text)
    #
    # def cut(self, event):
    #     self.copy()
    #     self.delete("sel.first", "sel.last")
    #
    # def paste(self, event):
    #     text = self.selection_get(selection='CLIPBOARD')
    #     self.insert('insert', text)
    #
    # def select_all(self, event):
    #     print 'pressed'
    #     self.tag_add(SEL, "1.0", END)
    #     self.mark_set(INSERT, "1.0")
    #     self.see(INSERT)
    #
    # def delete_all(self):
    #     print 'works'
    #     self.delete('1.0', END)


class ParameterInputText(CopyPasteText):
    """ This is a class which works like a Text widget,
        but with an appropriate iterator. Used in the second tab. """

    def __init__(self, root):
        Text.__init__(self, root)
        self._fromfile()

    def __iter__(self):
        """ Make the object iterable. If it is iterated,
        yield all the lines in the text editing window. """
        whatToIterate = self.get('1.0', END).strip()
        for i in whatToIterate.split(u'\n'):
            yield i

    def _fromfile(self, filename = defaultCfg):
        """ Read the start configuration from the config file
        and show it in the editing window. """
        if os.path.exists(filename): # if there's a configuration file,
            # copy its contents in the editing window.
            qText = codecs.open(filename, 'r', 'utf-8-sig').read()
            self.insert('1.0', qText)
            self.dataTakenFrom = filename


class StatTypeFrame(Frame):
    def __init__(self):
        Frame.__init__(self)
        self._add_all_checkbuttons()

    def _add_all_checkbuttons(self):
        dic = {'lemmas': u'Леммы подсвеченных слов',
               'pos': u'Части речи подсвеченных слов',
               'wordforms': u'Подсвеченные словоформы',
               'gr': u'Грамматические характеристики подсвеченных слов'}
        self.buttonList = {}
        self.buttonsAsTheyAre = {}
        self.chbState = []
        for stType in STAT_TYPES: # переменная STAT_TYPES — это словарь {название_типа_статистики : ее_считающая_функция}
            if stType in dic:
                buttonVar = IntVar() # соответствующая переменная
                buttonButton = Checkbutton(self, text = dic[stType], var = buttonVar, command = self._activate_chb_in_general)
                # todo: починить галочку
                buttonButton.pack()
                self.buttonList[stType] = buttonVar
                self.buttonsAsTheyAre[stType] = buttonButton

    def _activate_chb_in_general(self):
        """ If there're checkbuttons which are active,
        the checkbutton showing if we collect statistics mast be active. """
        if 'outerFrameButton' in self.__dict__:
            if self.list_of_stats_active():
                self.outerFrameButton.select()
            else:
                self.outerFrameButton.deselect()

    def list_of_stats_active(self):
        """ Compile a list of statistic function names which are active now.
        This means that these functions should be executed. """
        return [i for i in self.buttonList if self.buttonList[i].get() == True]


    # TODO: проверить связи!
    def save_last_and_deactivate_all(self):
        """ Compile a list of buttons active, copy it and deactivate all. """
        self.chbState = self.list_of_stats_active()
        for l in self.list_of_stats_active():
            self.buttonsAsTheyAre[l].deselect()

    def return_to_last_state(self):
        """ Restore all the checks active at the moment statistics was
         switched off from the outside. """
        if not self.list_of_stats_active():
            if self.chbState:
                for chbNAme in self.chbState:
                    self.buttonsAsTheyAre[chbNAme].select()
            else:
                for i in self.buttonsAsTheyAre:
                    self.buttonsAsTheyAre[i].select()

    def bind_to_general_frame_button(self, button):
        self.outerFrameButton = button


class TagWindow(Frame):
    """ A frame containing a listbox to check which tags should be in the final output. """

    def __init__(self, root):
        Frame.__init__(self, root)

        self._create_listbox(_WindowLabels.output_tags)
        self.lb.pack()

    def _create_listbox(self, possibleTagList):

        lb = Listbox(self, selectmode = EXTENDED, height = len(possibleTagList))
        tags = []
        for label, tag in possibleTagList: # label is a text in the interface, tag is a tag name in a dump.
            lb.insert(END, label)
            tags.append(tag)
        self.lb = lb
        self.tagsAvailable = tags

    def list_active(self):
        """ List the tags should be removed from dumps. """
        selectedToRemove = [self.tagsAvailable[int(i)] for i in self.lb.curselection()]
        return selectedToRemove


class DataReduceDescription(Frame):
    def __init__(self, root, *kw):
        Frame.__init__(self, root, *kw)

        self.pathToGeneralDefaults = None # путь, откуда можно брать данные
        self.defaultSettings = None # здесь будет словарь с настройками

        self._add_inner_wiggets()
#        self.substitute_defaults()

    def _add_inner_wiggets(self):
        """ initialize all the fields in the frame. """
        leftContext = Entry(self) # сколько удалить слева
        rightContext = Entry(self) # сколько удалить справа
        taglist = TagWindow(self) # окошко, где можно выбрать типы тегов
        # это всё привязано к переменным
        self.leftContext = leftContext
        self.rightContext = rightContext
        self.taglist = taglist

        Label(self, **_WindowLabels.context_left_label).grid(column = 0, row = 4)
        leftContext.grid(column = 0, row = 5)
        Label(self, **_WindowLabels.context_right_label).grid(column = 0, row = 2)
        rightContext.grid(column = 0, row = 3)
        Label(self, **_WindowLabels.tag_deletion_labels).grid(column = 0, row = 0)
        taglist.grid(column = 0, row = 1)

    def getsettings(self):
        """ Form a dic of an appropriate format if possible.
            If not, show error and do nothing. """
        try:
            lcData = self.leftContext.get()
            if lcData:
                lcData = int(lcData)
            else:
                lcData = 1000 # sorry for this dirty hotfix.
            rcData = self.rightContext.get()
            if rcData:
                rcData = int(rcData)
            else:
                rcData = 1000
            taglist = self.get_taglist()

            return {'leftcontext': lcData, 'rightcontext': rcData, \
                    'tags_to_delete': taglist}
        except:
            showerror(title = u'Error', message = u'Ошибка в общих настройках!')

    def get_taglist(self):
        """ Get the list of tags which should be deleted """
        return self.taglist.list_active()


class GeneralSettings(Frame):
    def __init__(self, root, *kw):
        Frame.__init__(self, root, *kw)
        self._init_all_buttons()

    def _init_all_buttons(self):
        self.statRequired = IntVar()
        stchb = Checkbutton(self, text = u'Запрашивать статистику', var = self.statRequired,
                            command = self._set_stframe_chb_values)
        self.statManagingButton = stchb # сохранено, потому что нужно управлять извне
        stchb.grid(column = 0, row = 0)

        self.isWhiteIP = IntVar()
        isWhiteIPbutton = Checkbutton(self, text = u'«Белый» IP', var = self.isWhiteIP)
        isWhiteIPbutton.grid(column = 0, row = 1)

        self.broadenContexts = IntVar()
        broadenContexts = Checkbutton(self, text = u'Расширять контексты', var = self.broadenContexts)
        broadenContexts.grid(column = 0, row = 6)

        self._add_downloading_limits()

        self.homonymyAllowed = IntVar()
        homonymy = Checkbutton(self, var = self.homonymyAllowed, **_WindowLabels.homonymy_allowed_label)
        homonymy.grid(column = 0, row = 5)

        self.homonymy = homonymy

    def _add_downloading_limits(self):
        self.snippetLimit = Entry(self)
        self.randomizerRequired = IntVar()
        randomizerChB = Checkbutton(self, text = u'Случайная сортировка', var = self.randomizerRequired)
        self.randomizerChB = randomizerChB

        Label(self, text = u'Максимум скачанных страниц:').grid(column = 0, row = 2)
        self.snippetLimit.grid(column = 0, row = 3)
        randomizerChB.grid(column = 0, row = 4)

    def statistics_required(self):
        """ Return the boolean value signing if we should count statistics. """
        return bool(self.statRequired.get())

    def ip_is_in_white_list(self):
        return bool(self.isWhiteIP.get())

    def example_number(self):
        try:
            tmp = int(self.snippetLimit.get())
        except:
            tmp = None
        return tmp

    def randomize_output(self):
        return bool(self.randomizerRequired.get())

    def homonymy_only(self):
        return bool(self.homonymyAllowed.get())

    # def bind_to_notebook(self, notebook, tabNumber):
    #     self.linkToNb = notebook
    #     self.tabNumber = tabNumber

    def bind_to_statistics_frame(self, stFrame):
        self.correspondingFrame = stFrame
        stFrame.bind_to_general_frame_button(self.statManagingButton)

    def _set_stframe_chb_values(self):
        if not self.statRequired.get():
            self.correspondingFrame.save_last_and_deactivate_all()
        else:
            self.correspondingFrame.return_to_last_state()

    def hide_checkboxes(self):
        self.homonymy.grid_forget()
        self.randomizerChB.grid_forget()

    def show_checkboxes(self):
        self.homonymy.grid(column = 0, row = 5)
        self.randomizerChB.grid(column = 0, row = 4)


def copy_values_to_statistic_list(innerFunc):
    """ A func to decorate the ones which call the downloading.
        Copy statistic flags from the frame to the self.stlist variable """
    def func(self):
        if self.settings.statistics_required():
            keys = self.statTab.list_of_stats_active()
            self.stlist = keys
        else:
            self.stlist = []
        return innerFunc(self)
    return func


def block_buttons(innerFunc):
    def func(self):
        self.b1['state'] = 'disabled'
        self.b2['state'] = 'disabled'
        innerFunc(self)
        self.b1['state'] = 'active'
        self.b2['state'] = 'active'
    return func

class SettingHybrid(Frame):
    def __init__(self, *kw):
        Frame.__init__(self, *kw)
        self.general = GeneralSettings(self)
        self.reducing = DataReduceDescription(self)
        self.general.pack()
        self.reducing.pack()

    def getsettings(self):
        fromReducing = self.reducing.getsettings()
        fromReducing['homonymy_in_main_allowed'] = self.general.homonymy_only()
        fromReducing['exlim'] = self.general.example_number()
        fromReducing['whiteip'] = self.general.ip_is_in_white_list()
        fromReducing['rand'] = self.general.randomize_output()
        fromReducing['contexts'] = bool(self.general.broadenContexts.get()) # todo arrange this
        return fromReducing

    def bind_to_statistics_frame(self, stFrame):
        self.general.bind_to_statistics_frame(stFrame)

    def statistics_required(self):
        return self.general.statistics_required()

    def hide_checkboxes(self):
        self.general.hide_checkboxes()

    def show_checkboxes(self):
        self.general.show_checkboxes()


def process_unified_task(task):
    """ Given a unified task dic, process it. """
    taskType, taskArgs = task['type'], task['args']
    data = None
    if taskType == 'text':
        # print taskArgs
#        data = call_raw_text_query(*taskArgs)
        data = execute_query_seq_with_settings(*taskArgs)
    elif taskType == 'url':
#        data = call_url_query(*taskArgs) # may be None.
        url, dst, settings, dstIsFile, statistics = taskArgs
        url = urllib.unquote(str(url)).decode('cp1251')
        data = execute_url_query(url, dst, settings, dstIsFile, statistics)
    if data:
        data['query'] = task['text_query']
    else:
        data = {'query': task['text_query'], 'full_disconnect': True, 'type': 'atom'}
    return data


def executor(tasks, awaited, results, callCounter):
    """ Process the data in a queue if there is something to process. """
    while True:
            task = tasks.get()
            data = process_unified_task(task)
            results.put(data)
            callCounter += (download_page.callCounter - int(callCounter)) # Sorry.
            awaited -= 1


def _show_warnings_specified(result, addition):
    """
    On getting the result of url processing, analyze it and show the necessary warning, if necessary.
    """
    url = result['query'].strip()
    url = url[:50] + u'...' + url[-80:]
    query = u'Запрос: %s\n' % url
    if 'full_disconnect' in result:
        showwarning(message = query + u'Ошибка подключения.' + addition)
        return
    if result['interrupted'] and not result['extended']:
        showwarning(message = query + u'Выдача неполная, и не все контексты были расширены.' + addition)
    elif result['interrupted']:
        showwarning(message = query + u'Выдача неполная.' + addition)
    elif not result['extended']:
        showwarning(message = query + u'Не все контексты были расширены.' + addition)
    elif result['type'] == 'atom' and result['tree'] is None:
        showinfo(message=query + u'выполнен. Ничего не найдено.' + addition)
    else:
        showinfo(message=query + u'выполнен.' + addition)


def _form_warning_text(disconnected, interrupted, notExt, nothingFound, inapprQ, invalCorp):
    text = []
    if disconnected:
            text.append(u'Не удалось установить соединение: %s' % u', '.join(disconnected))
    if interrupted:
            text.append(u'При сборе информации из следующих корпусов было прервано соединение: %s' % u', '.join(interrupted))
    if notExt and interrupted:
            text.append(u'Не удалось расширить контексты в корпусах: %s' % u', '.join(interrupted))
    if nothingFound:
            text.append(u'В следующих корпусах по запросу ничего не найдено: %s' % u', '.join(nothingFound))
    if inapprQ:
            text.append(u'К следующим корпусам сделан невозможный запрос: %s' % u', '.join(inapprQ))
    if invalCorp:
            text.append(u'Поиск невозможен по корпусам: %s' % u', '.join(invalCorp))
    if text:
            return u'\n'.join(text)
    else:
            return u''


class SmartTk(Tk):
    """ A window class showing a dialogue window according with the number of tasks undone."""
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.tasksUndone = 0
        self.processBound = []

    def _terminate_all_and_exit(self):
        """ Terminate all the processes bound and exit the program. """
        for i in self.processBound:
            i.terminate()
        Tk.destroy(self)

    def destroy(self):
        if self.tasksUndone == 0:
            self._terminate_all_and_exit()
        else:
            val = askokcancel(**_DialogueLabels.exit_message)
            if val:
                self._terminate_all_and_exit()


class TabInterface:
    def __init__(self):

        self.tasks = None
        self.mainTerminated = None
        self.results = None
        self.awaited = None

        self.reqParser = RawQueryParser()

        self.defaultCfg = defaultCfg
        self.stlist = STAT_TYPES.keys()

        # set main window parameters
        mainWindow = SmartTk()
        mainWindow.title(_WindowLabels.window_title)
        self.root = mainWindow
        mainWindow.minsize(650, 450)

        # there are two frames with different finctions.
        # In fact, they work separately but use the same set of settings.
        generalframe = SettingHybrid(mainWindow)
        tabframe = Frame(mainWindow)

        self.settings = generalframe

        nb = Notebook(tabframe)
        nbUrlTab = Frame()
        nbFileEditingTab = Frame()
        nbStatTab = StatTypeFrame()
        self.statTab = nbStatTab
        self.homeDir = None


        qField = ParameterInputText(nbFileEditingTab)
        self.qField = qField
        qReadingButton = Button(nbFileEditingTab, text = u'OK', command = self.get_request_from_raw_query_window)

        self.urlText = CopyPasteText(nbUrlTab)
        urlButton = Button(nbUrlTab, text = u'OK', command = self.get_query_from_url_window)

        self.urlText.pack(fill=BOTH, expand=1)
        urlButton.pack()

        self.b1 = urlButton
        self.b2 = qReadingButton

        nb.add(nbFileEditingTab, text = tabs['file'])
        nb.add(nbUrlTab, text = tabs['url'])
        nb.add(nbStatTab, text = tabs['st'])

        minTabFrameWidth = 0
        for tab in nb.tabs():
            minTabFrameWidth += len(nb.tab(tab)['text'])

        self.root.config(width = minTabFrameWidth + 200)

        qField.pack(fill=BOTH, expand=1)
        qReadingButton.pack()
        #nbUrlTab.pack()
        nb.pack(fill=BOTH, expand=1)

        self.nb = nb # to manage tabs

        generalframe.pack(expand=0, side = 'left')
        tabframe.pack(fill=BOTH, expand=1)

        generalframe.bind_to_statistics_frame(nbStatTab)

        self.enable_keyboard_managing()
        self._add_menu()

    def _process_request_dict(self, requestDic):
        """ In an one-process version, this is the main executor. """
        data = process_unified_task(requestDic)
        self.calls = download_page.callCounter
        self.results.put(data)


    @copy_values_to_statistic_list
    def get_request_from_raw_query_window(self):
        """ Execute the query in the window. """
        # поместить в общую очередь описание запроса: тип (text/url), настройки,
        settings = self.settings.getsettings() # словарь с настройками.
        if settings:
            # print settings
            self.reqParser.read_corpora_query(self.qField)
            if self.reqParser.last_is_appropriate():
                path = self._ask_path_to_directory()
                if path:

                    setParams = {}

                    if settings["rand"]:
                        setParams["sort"] = "random"
                        setParams["seed"] = unicode(random.randint(1, 65356))

                    if settings['homonymy_in_main_allowed']:
                        setParams["mycorp"] = u'%28%28tagging%253A%2522manual%2522%29%29'

                    if setParams:
                        request = self.reqParser.get_subcorpora_query_list(**setParams)
                    else:
                        request = self.reqParser.get_subcorpora_query_list()
                    statistics = self.stlist
                    queueData = {'type': 'text',
                                 'args': (request, self.homeDir, settings, statistics),
                                 'text_query': self.qField.get('1.0', END)}
                    self._process_request_dict(queueData)
            else:
                errorText = _DialogueLabels.generate_raw_query_error(self.reqParser.lastUnread)
                showerror(**errorText)

    def _ask_path_to_file(self):
        """ Ask a path to the destination file. If a dir has been already specified,
        open the choice window showing this dir. """
        if not self.homeDir:
            fullPath = asksaveasfilename(**_DialogueLabels.save_output_file_choice)
        else:
            fullPath = asksaveasfilename(initialdir = self.homeDir, **_DialogueLabels.save_output_file_choice)
        if fullPath:
            dir, filename = os.path.split(fullPath)
            if dir:
                self.homeDir = dir
        return fullPath

    def _ask_path_to_directory(self):
        """ Ask a path to the destination directory. If a dir has been already specified,
        open the choice window showing this dir. """
        if not self.homeDir:
            path = askdirectory(**_DialogueLabels.save_output_directory_choice)
        else:
            path = askdirectory(initialdir = self.homeDir, **_DialogueLabels.save_output_directory_choice)
        if path:
            self.homeDir = path
        return path

    def _get_url_specified(self):
        """ Get the URL specified in the GUI, then convert it to the URL to get dumps. """
        url = self.urlText.get('1.0', END)
        url = url.replace(u'http://search.ruscorpora.ru/search.xml?', u'http://search.ruscorpora.ru/dump.xml?')
        url = url.replace(u'http://search-beta.ruscorpora.ru/search.xml?', u'http://search.ruscorpora.ru/dump.xml?')
        return url

    @copy_values_to_statistic_list
    def get_query_from_url_window(self):
        settings = self.settings.getsettings()
     #   timeMarker = get_date_as_string()
        url = self._get_url_specified()
        if url:
            if not self.settings.statistics_required():
                dstPath = self._ask_path_to_file()
                isFilename = True
            else:
                dstPath = self._ask_path_to_directory()
                isFilename = False

            if dstPath:
                queueData = {'type': 'url',
                             'args': (url, dstPath, settings, isFilename, self.stlist),
                             'text_query': url}

                self._process_request_dict(queueData)

    def change_tab(self, event):
        """ Enable the next or the previous tab """
        # setting the list of tabs available

        currentTab = self.nb.select()
        allTabs = self.nb.tabs()
        currentTabNum = allTabs.index(currentTab)

        if event.keysym == 'Right':
            if currentTabNum + 1 < len(allTabs):
                newTabNum = currentTabNum + 1
            else:
                newTabNum = 0

        elif event.keysym == 'Left':
            if not currentTabNum - 1 < 0:
                newTabNum = currentTabNum - 1
            else:
                newTabNum = len(allTabs) - 1

        else:
            return

        newIndex = allTabs[newTabNum]
        self.nb.select(newIndex)

    def modify_setting_window(self, event):
        tabsWhereHomonymyAndRandomDisabled = [1]
        currentTab = self.nb.index(self.nb.select())
        if currentTab in tabsWhereHomonymyAndRandomDisabled:
            self.settings.hide_checkboxes()
        else:
            self.settings.show_checkboxes()

    def _filequery_to_file(self):
        path = asksaveasfilename(**_DialogueLabels.save_query_choice) # save_query_choice
        try:
            with codecs.open(path, 'w', 'utf-8') as f:
                f.write(self.qField.get('1.0', END))
        except:
            showerror(**_DialogueLabels.save_query_error) # save_query_error


    def _add_menu(self):
        menubar = Menu(self.root)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label = _WindowLabels.cascade_file_save_query, command = self._filequery_to_file)
        menubar.add_cascade(label = _WindowLabels.cascade_file_label, menu=filemenu)

        self.root.config(menu=menubar)

    def enable_keyboard_managing(self):
        self.root.bind(u'<Alt-Right>',  self.change_tab) # Alt+arrows for Windows.
        self.root.bind(u'<Alt-Left>',  self.change_tab)
        self.root.bind(u'<Mod2-Right>',  self.change_tab) # same for Mac
        self.root.bind(u'<Mod2-Left>',  self.change_tab)
        self.root.bind(u'<<NotebookTabChanged>>', self.modify_setting_window)


    def message_publisher(self):
        if not self.results.empty():
            if not self.settings.getsettings()['whiteip']:
                addition = u'\nОбращений к корпусу с момента старта программы: %s' % int(self.calls)
            else:
                addition = u''
            result = self.results.get()
            if not result:
                pass
            elif result['type'] == 'multiple':
                query = u'Запрос обработан: %s\n' % result['query']
                params = ['disconnected', 'interrupted', 'notExtended', 'nothingFound', 'inappropriateQuery', 'invalidCorpNames']
                args = [result[i] for i in params]
                msg = _form_warning_text(*args)
                if not msg:
                        showinfo(message=query + addition)
                else:
                        showwarning(message=query + msg + addition)
            elif result['type'] == 'atom':
                    _show_warnings_specified(result, addition)
        self.root.after(200, self.message_publisher)

    def run(self):
        self.calls = 0
        self.results = Queue()
        self.root.after(200, self.message_publisher)
        self.root.mainloop()


if __name__ == '__main__':
    ti = TabInterface()
    ti.run()
