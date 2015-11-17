# What is ruscorporaXML?

RuscorporaXML is a desktop client for ruscorpora.ru. The program prevents you from turning over multiple pages of ruscorpora's output downloading all the necessary examples as a single XML file. You also can straight away collect some statistics on the data you download.

## Disclaimers
* You cannot use the program for commercial purposes. It was developed to facilitate linguistic research being made with the use of the Russian National Corpus. You also should mind [these terms and conditions](http://www.ruscorpora.ru/corpora-usage.html).
* The number of requests to the corpus you can make is limited: you can only make 1000 requests before you are banned for a while. 

# Requirements and installation
To run this, you'll need to have Python 2.7 installed (**Disclaimer**: you cannot run a Python2.7 program with a Python3 interpreter!). [LXML](http://lxml.de/tutorial.html) (at least v.3.3) is also required.

## Linux
For Linux, open the Terminal and type the following commands:
```
sudo apt-get install python
sudo apt-get install python-pip
pip install lxml
```
(The first one is supposedly redundant as Python is usually pre-installed on Linux).

## Mac OS
If you are on Mac, you should have a Python interpreter installed by default. However, you may probably not have the LXML lib. I *strongly recommend* you to update your Python using an installer from the [official Python site](https://www.python.org/downloads/). An up-to-date version of Python contains the package manager `pip`, so you will be able to install LXML by just running the following command in your Terminal: `pip install lxml`.

## Windows
(Un)fortunately, I do not have an active copy of Windows on my computer (and [have nothing to do with it](http://bash.im/quote/436599)), so I cannot instruct you. Contributions are welcome.

# What about a standalone app?
There was a plan to build a standalone app for Mac (and also for Linux) but I do not know when this may come true. As for a Windows standalone version, I *do know* it is desired but this question is unresolved as I do not develop for Windows at all.
