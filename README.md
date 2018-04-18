# Firebox

a mailbox on firebase

## Quick start

Install `pyrebase`:

    $ pip install pyrebase

Decide on a mailbox name. For example, `mymail`.

Copy the Firebase key file over and modify the path in `config.json` if needed.

On one computer, do

    $ python
    >>> import firebox
    >>> firebox.test_sink('mymail')

On another, do

    $ python
    >>> import firebox
    >>> firebox.test_source('mymail')

Watch the show.

## Introduction

This module handles communication between two separate computers or devices, 
connected only by Firebase. A source device can send work to a sink device and
grab the result of the work when the sink device is done. For example, a front-
end device (kivy) can request that another device (card reader, weight sensor) 
gather sensor data and send the data when it's ready. Then when the data is 
ready, the card reader or weight sensor signals the kivy to grab data. The kivy
receives the signal, pulls the data and displays it on-screen.

And the best part is that all of this is asynchronous.

## Using on a source

A source is a computer or device that wants to send work to a sink device and 
get the result back. Source functionality is provided by the 
`firebox.MailboxSource` class. When creating the class, pass a string into the 
initialization. This is the name of the mailbox that the `MailboxSource` works 
on.

The source must provide a **callback** that handles the received data. This 
callback has the signature `<callback>(msg, sender)` where `msg` is a firebase
stream message and `sender` is the `MailboxSource` that called the callback.

Inside the callback, call `sender.pop_data()` to see what data was changed. You
only have one chance to do this because the data value in Firebase is deleted 
when you call `pop_data()`.

The data returned can be `None`, this indicates that the data was cleared. 
So either there is no valid data from the sink or you never raised the flag
and now you are getting a random event.

Sample callback:

    def src_handle(msg, sender):
        print('Handling source flag lowered')
        print('Grabbing work: "{}"'.format(sender.pop_data()))

Registering the callback:

    src = firebox.MailboxSource('card_reader')
    pyre_stream = src.register_cb(src_handle)

To raise the flag and signal to the sink device to begin work:

    src.raise_flag()

When exiting the main thread, to stop the listening thread (so that the Python
process exits):

    pyre_stream.close()

Note: if the sink is already processing work (in its callback), the data will 
be sent to the source regardless of flag status. Make sure the source callback
takes into account the application state before acting on the callback.

## Using on a sink

A sink is a device that can fulfil the work order from a source. Sink 
functionality is provide by the `firebox.MailboxSink` class. Remember to pass in
the name of the mailbox to listen for.

Same as the `MailboxSource` class, the sink must provide a callback with the
same signature as above. But inside the callback, assign to `sender.data` to 
push the data to Firebase.

Sample callback:

    def sink_handle(msg, sender):
        print('Handling sink flag raised')
        result = expensive_io_operation()
        print('Done work')
        sender.data = result

Registering the callback:

    snk = MailboxSink('card_reader')
    pyre_stream = snk.register_cb(sink_handle)

When exiting the main thread, to stop the listening thread (so that the Python
process exits):

    pyre_stream.close()

Flag lowering is handled automatically after the callback exits.

## Removing callbacks

To prevent the callback executing when you don't want it to, you can remove the
callback you registered with:

    pyre_stream = src.register_cb(src_handle)
    pyre_stream.close()

You can add the callback again later.

You **must** remove all callbacks before exiting your app (eg in
`kivy.app.App.on_stop()`) for the main Python process to exit.