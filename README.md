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

Inside the callback, access `sender.data` (but don't modify it) to see what
data was changed.

Sample callback:

    def src_handle(msg, sender):
        print('Handling source flag lowered')
        print('Grabbing work: "{}"'.format(sender.data))

Registering the callback:

    src = firebox.MailboxSource('card_reader')
    src.register_cb(src_handle)

To raise the flag and signal to the sink device to begin work:

    src.raise_flag()

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
    snk.register_cb(sink_handle)

Flag lowering is handled automatically after the callback exits.

## Removing callbacks

Removing callbacks can't be done. So only register as many callbacks as you 
need, and make sure the callback can decide if it should or should not run 
based on whether the application is in a state that can accept the data.