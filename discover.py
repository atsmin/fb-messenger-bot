from bluetooth.ble import DiscoveryService
import requests

URL = 'https://ancient-sea-14004.herokuapp.com/greet'

service = DiscoveryService()
devices = service.discover(2)

if devices:
    mac_addrs = [addr for addr, name in devices]
    requests.post(URL, data={'mac_addrs': mac_addrs})
