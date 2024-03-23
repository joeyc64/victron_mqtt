#
# victron_mqtt.py
# V1.00 - 03-12-2024
# Connects to a victron solar controller via bluetooth and writes the data to a mqtt broker via wifi
# Runs on a Raspberry Pi Pico W
# Additional libs required to install with Thonny/Tools/Manage packages:
#   umqtt.simple
#   copy
# Also copy stripped down AES-crypto lib "victron_aes.py" to the PICO
#

import sys
import machine
import network
import time
import uasyncio as asyncio
import aioble
import bluetooth
# extra libs to include into Thonny:
from umqtt.simple import MQTTClient
import victron_aes


victron_mac="fdad42d6356b" # see label on solar charger
victron_key="1cff3b18a75d5025bf7c9f2885498b76" # you can find this in the Victron App - google where exactly it is

# WLAN-Konfiguration
wlanSSID = 'yourSSID'
wlanPW = 'yourpassword'
network.country('DE')

# MQTT-Konfiguration
mqttBroker = '192.168.178.73'
mqttClient = 'pico'
mqttUser = 'mqttuser'
mqttPW = ''

# Status-LED 
led_onboard = machine.Pin('LED', machine.Pin.OUT, value=0)

def blinkCode( mode ):
    #            WIFI  BLUETOOTH   MQTT
    blinker = [ [1,1], [0.5,0.5], [2,2] ]
    
    for i in range(0,3):
        led_onboard.on()
        time.sleep( blinker[mode][0] )
        led_onboard.off()
        time.sleep( blinker[mode][1] )


# Funktion: WLAN-Verbindung herstellen
def wlanConnect():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        print('Connect to WIFI:', wlanSSID)
        wlan.active(True)
        wlan.connect(wlanSSID, wlanPW)
        for i in range(10):
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            print('.')
            time.sleep(1)
    if wlan.isconnected():
        print('WIFI connected / status:', wlan.status())
    else:
        print('NO WIFI connection / status:', wlan.status())
        led_onboard.off()
        time.sleep(15)
    return wlan

# Funktion: Verbindung zum MQTT-Server herstellen
def mqttConnect():
    if mqttUser != '' and mqttPW != '':
        #print("MQTT-Verbindung herstellen: %s mit %s als %s" % (mqttClient, mqttBroker, mqttUser))
        client = MQTTClient(mqttClient, mqttBroker, user=mqttUser, password=mqttPW )
    else:
        #print("MQTT-Verbindung herstellen: %s mit %s" % (mqttClient, mqttBroker))
        client = MQTTClient(mqttClient, mqttBroker)

    client.connect()
    print('MQTT connected')

    return client


async def scanVictron():
    dData = {}
    lastData = []
    # Scan for 5 seconds, in active mode, with very low interval/window (to
    # maximise detection rate).
    async with aioble.scan(5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            # See if it matches our name and the environmental sensing service.            
            #addr = ''.join('{:02x}'.format(x) for x in result.device.addr) # mac addr, e.g. "fdad42d6356b"
            #print( "Name: '{}', MAC: '{}', RSSI: {}".format(result.name(), addr, result.rssi) )
            if result.adv_data != None and result.device.addr==mac:
                #print( ''.join(' {:02x}'.format(x) for x in result.adv_data) )
                if  result.adv_data[14]==key[0]: # check if first byte of key is same
                    #print("")
                    data = result.adv_data[7:] # here starts the 'extra manufacturer data'
                    if data==lastData: # same record as last? skip if no changes to data
                        continue
                    lastData = data
                    #print( ''.join(' {:02x}'.format(x) for x in data) )
                    v = data[5]+data[6]*256
                    counter = victron_aes.Counter(initial_value = v )
                    # man, this took me a while to figure out... Victron wants the nonce/counter the other way round
                    c = []
                    for i in range(len(counter._counter)):
                        c.append( counter._counter[len(counter._counter)-1-i] )
                    counter._counter = c
                    #
                    encryptedData = data[8:]
                    aes = victron_aes.AESModeOfOperationCTR(key,counter) # https://github.com/ricmoo/pyaes/
                    decrypted = aes.decrypt(encryptedData)                   
                    #print( ''.join(' {:02x}'.format(x) for x in decrypted) )
                    # now extract the values (Solar Charger-Format)
                    # https://github.com/keshavdv/victron-ble
                    dData={"device_state": decrypted[0], # Charge State: 0-Off, 3-Bulk, 4-Absorption, 5-Float
                        "charger_error": decrypted[1], #  0-No Error (more her: https://github.com/keshavdv/victron-ble/blob/main/victron_ble/devices/base.py)
                        "batt_voltage": (decrypted[2]+decrypted[3]*256)*0.01,
                        "batt_current": (decrypted[4]+decrypted[5]*256)*0.1,
                        "yield_today": (decrypted[6]+decrypted[7]*256)/100,
                        "pv_power": (decrypted[8]+decrypted[9]*256)}
                    #print( dData )
    return dData


async def main():
    global dData
    dData = await scanVictron()

###### MAIN
wlan = None
client = None
key = bytes.fromhex(victron_key)
mac = bytes.fromhex(victron_mac)

while True:
    # check for valid WIFI connection
    if wlan==None or not wlan.isconnected():
        wlan = wlanConnect()
        if not wlan.isconnected():
            print("no WIFI connection, try again...")
            blinkCode(0) # blink error (includes wait time)
            continue
    #print("RSSI=",wlan.status('rssi'))
    # get data from Victron Solar-Charger device via Bluetooth advertising protocol
    dData = {}
    asyncio.run(main())
    if len(dData)==0:
        print("no data from Victron bluetooth - not in range?")
        blinkCode(1) # blink error (includes wait time)
    #else:
    #    print( dData )
    # post data to MQTT broker/server
    try:
        if client==None:
            client = mqttConnect()
        # post data
        if len(dData)>0:
            led_onboard.on() # data is sent, all OK
            for i in dData:
                #print( i, dData[i] )
                client.publish( "victron/"+victron_mac+"/"+i, str(dData[i]))
            print("MQTT data published")
    except OSError:
        try:
            client = mqttConnect()
        except OSError:
            print("Error, no MQTT-connection, reconnect failed...")
            led_onboard.off()
            client = None # force new connect
            blinkCode(2) # blink error (includes wait time)
        
