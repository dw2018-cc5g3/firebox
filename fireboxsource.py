import firebox
import time

def source_handle(msg, sender):
    print('Found a card with CAN {}'.format(sender.pop_data()))

src = firebox.MailboxSource('card_reader')
pyre_stream = src.register_cb(source_handle)

print('Raising flag')
src.raise_flag()

time.sleep(10)
print('10 secs is up, exiting...')
pyre_stream.close()