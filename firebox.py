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
    """Base mailbox class. Implements init, flag and data properties, and 
    stream event handler skeleton
    """
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
        """This is the actual function that is called when the flag in firebase
        changes and the stream event fires.

        message: the firebase stream message
        val: the desired data value to watch for (True or False)
        cb: callback to call if message['data'] == val
        post: postamble to call after the callback (used to lower the flag)
        """
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
        """Register a callback for when the flag lowers. This method returns a
        pyrebase.Stream object that you should save (see last paragraph).

        callback is a function that takes 2 params, the firebase stream message
        and the MailboxSource that called it, and returns None
        
        To grab the data, in your callback, do
            <your_data_variable> = <MailboxSink>.pop_data()
        
        You can only grab the data once before it is cleared from Firebase, to
        avoid any double-reading or reading of stale data.
        
        The stream handler runs in a separate thread and will stay alive even
        after the main thread has exited! Call <returned stream object>.close()
        to stop the handler thread, when you no longer need it around.
        """
        # Attach to firebase_db: /<mailbox>/task_flag
        # Watch for task_flag: False (flag lowering)
        # No postamble needed here.
        # functools.partial is used to neatly encapsulate the val, cb, and post
        # params without having to create my own new method
        return self._db.child(self.mailbox).child('task_flag').stream(
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
        """Register a callback for when the flag raises. This method returns a
        pyrebase.Stream object that you should save (see last paragraph).

        callback is a function that takes 2 params, the firebase stream message
        and the MailboxSink that called it, and returns None
        
        When the task is done, in your callback, do
            <MailboxSink>.data = <your_data>
        
        The stream handler runs in a separate thread and will stay alive even
        after the main thread has exited! Call <returned stream object>.close()
        to stop the handler thread, when you no longer need it around.
        """
        # Postamble is needed to lower the flag.
        # Watching for the raised flag, so val=True
        return self._db.child(self.mailbox).child('task_flag').stream(
            ft.partial(self._handler, val=True, cb=callback,
                post=self.lower_flag))

# Testing code.

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
    return snk.register_cb(sink_handle)

def test_source(mailbox):
    src = MailboxSource(mailbox)
    def src_handle(msg, sender):
        print('Handling source flag lowered')
        print('Grabbing work: "{}"'.format(sender.pop_data()))
    src_pyrestream = src.register_cb(src_handle)
    src.raise_flag()
    return src_pyrestream