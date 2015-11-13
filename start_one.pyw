# -*- coding: utf-8 -*-


from tabgui import TabInterface, block_buttons


class OneProcessInterface(TabInterface):

    @block_buttons
    def get_request_from_raw_query_window(self):
        TabInterface.get_request_from_raw_query_window(self)

    @block_buttons
    def get_query_from_url_window(self):
        TabInterface.get_query_from_url_window(self)


if __name__ == '__main__':
    ti = OneProcessInterface()
    ti.run()
