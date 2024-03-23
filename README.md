# victron_mqtt
Micropython connecting to a Victron Solar Charger via Bluetooth and publishing values to a MQTT broker via Wifi
This is used on a Raspberry Pi Pico W
Since I couldn't find anything working on Micropython getting data out of a Victron solar charger I decided to post my solution. Feel free to use, modify or do whatever you want to do with it.
Victron is using an AES-128Bit-CTR encryption for which I stripped down an existing library to get it working on a Pico. The cryptolib from micropython does not support CTR mode (yet) so I looked for another solution.
