"""
Firebase-powered mailbox
It's not actually a task queue
"""

import functools as ft

import os
import pyrebase
import json

with open('config.json') as f:
    config = json.load(f)

# mailbox_slot
# +-- task_flag: bool
# +-- result: Object

_fb = pyrebase.initialize_app(config)

class MailboxBase():
    def __init__(self, mailbox):
        self._db = _fb.database()
        self.mailbox = mailbox
    
    def get_flag(self):
        return self._db.child(self.mailbox).child('task_flag').get().val()
    
    def set_flag(self, val):
        self._db.child(self.mailbox).child('task_flag').set(bool(val))

    flag = property(get_flag, set_flag)

    def lower_flag(self):
        self.flag = False
    
    def raise_flag(self):
        self.flag = True

    def get_data(self):
        return self._db.child(self.mailbox).child('data').get().val()
    
    def set_data(self, val):
        self._db.child(self.mailbox).child('data').set(val)

    data = property(get_data, set_data)

    def _handler(self, message, val, cb, post):
        # print('Entered _handler: message={} val={} cb={}'
        #     .format(message, val, cb))
        if (message['event'] in ('put', 'patch')
                and message['path'] == '/'
                and message['data'] == val):
            # print('Entered _handler\'s callback block: message={} val={} cb={}'
            #     .format(message, val, cb))
            cb(message, self)
            post()
            
    def register_cb(self, cb):
        raise NotImplementedError


class MailboxSource(MailboxBase):
    """Firebase "mailbox" source. Signals a sink component to begin a task and
    waits until a result is available.

    Register a callback with register_cb().
    Then when you want to start a task, do raise_flag()
    """

    def register_cb(self, callback):
        """Register a callback for when the flag lowers.

        callback is a function that takes 2 params, the firebase stream message
        and the MailboxSource that called it, and returns None
        
        To grab the data, in your callback, do
            <your_data_variable> = <MailboxSink>.data
        """
        self._db.child(self.mailbox).child('task_flag').stream(
            ft.partial(self._handler, val=False, cb=callback,
                post=lambda: None))
    
    def pop_data(self):
        """Grab data and clear it from Firebase
        """
        result = self.data
        self.data = None
        return result


class MailboxSink(MailboxBase):
    """Firebase "mailbox" sink. Listens to signal from the source and performs 
    a task then.

    Register a callback with register_cb().
    
    """    
    def register_cb(self, callback):
        """Register a callback for when the flag raises.

        callback is a function that takes 2 params, the firebase stream message
        and the MailboxSink that called it, and returns None
        
        When the task is done, in your callback, do
            <MailboxSink>.data = <your_data>
        """
        self._db.child(self.mailbox).child('task_flag').stream(
            ft.partial(self._handler, val=True, cb=callback,
                post=self.lower_flag))
    
def test_sink(mailbox):
    import time
    import secrets
    snk = MailboxSink(mailbox)
    def sink_handle(msg, sender):
        print('Handling sink flag raised')
        rand = secrets.token_urlsafe(8)
        print('Pretending to do work id {}'.format(rand))
        time.sleep(5)
        print('Done work')
        sender.data = rand
    snk.register_cb(sink_handle)

def test_source(mailbox):
    src = MailboxSource(mailbox)
    def src_handle(msg, sender):
        print('Handling source flag lowered')
        print('Grabbing work: "{}"'.format(sender.pop_data()))
    src.register_cb(src_handle)
    src.raise_flag()