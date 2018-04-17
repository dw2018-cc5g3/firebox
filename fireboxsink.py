import firebox
import reader

def sink_handle(msg, sender):
   print('Now accepting card: Tap here...')
   can = reader.block_for_can()
   sender.data = can
   print('Sent CAN: {}'.format(can))

snk = firebox.MailboxSink('card_reader')
snk.register_cb(sink_handle)

print('Standing by')
