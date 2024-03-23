# victron_mqtt
Micropython script connecting to a Victron Solar Charger via Bluetooth and publishing values to a MQTT broker via Wifi<br>
This is used on a Raspberry Pi Pico W<br>

Since I couldn't find anything working on Micropython getting data out of a Victron solar charger I decided to post my solution. Feel free to use, modify or do whatever you want to do with it.<br>
Victron is using an AES-128Bit-CTR encryption for which I stripped down an existing library to get it working on a Pico. The cryptolib from micropython does not support CTR mode (yet) so I looked for another solution.<br>

Additional libs required to install with Thonny/Tools/Manage packages:<br>
* umqtt.simple<br>
* copy<br>

Also copy stripped down AES-crypto lib "victron_aes.py" to the PICO.<br>
Modify the victron_mqtt.py with your Wifi and MQTT broker settings.<br>

