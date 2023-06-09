import requests
import json
import hashlib
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

router_key = os.getenv("ROUTER_KEY")
router_pwd = os.getenv("ROUTER_PWD")
home_url = 'http://192.168.31.1/cgi-bin/luci/api/xqsystem/login'


def mi_router_session():
    global devices_endpoint
    sha_from_pwd = hashlib.sha1(router_pwd.encode('utf-8') + router_key.encode('utf-8')).hexdigest()
    current_time = int(datetime.utcnow().timestamp()*1000//1)
    nonce = "0_a0:78:17:9d:26:91_" + str(current_time) + "_4478"
    sha_pwd = hashlib.sha1(
        (nonce + sha_from_pwd).encode('utf-8')).hexdigest()
    login_data = {
        'username': 'admin',
        'password': sha_pwd,
        'logtype': 2,
        'nonce': nonce
    }
    session = requests.session()
    req = session.post(home_url, data=login_data)
    token = req.json()['token']
    devices_endpoint = f'http://192.168.31.1/cgi-bin/luci/;stok={token}/api/misystem/devicelist'

    return session


def read_dump(file):
    dump = open(file, "r")
    parsed_dump = json.load(dump)
    dump.close()
    return parsed_dump


def get_active_macs():
    session = mi_router_session()
    home_page = session.get(devices_endpoint)
    users = home_page.json()
    users_data = []
    for i in users['list']:
        users_data.append(i['mac'])

    return users_data


def get_all_known_macs(dump):
    known_macs_list = []
    for name in dump:
        known_macs_list += dump[name]
    return known_macs_list


def convert_to_string():
    guests_count = 0
    our_macs = read_dump('macs_dump.json')
    current_macs = get_active_macs()
    response = ''
    checked_names = []
    total_macs_list = get_all_known_macs(our_macs)
    for mac in current_macs:
        for name in our_macs:
            if mac in our_macs[name] and name not in checked_names and name != "Devices":
                checked_names.append(name)
                response += f'{name}\r\n'
    for mac in current_macs:
        if mac not in total_macs_list:
            guests_count += 1
    if response == '':
        response = 'никого, даже '
    return f'Сейчас в офисе..\r\n{response}гостей {str(guests_count)}'
