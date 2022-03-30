import socket
import sys
import httpx
import random
import numpy as np
from tqdm import tqdm

STATE_ID = 12
COORD_URL = f'http://localhost:8530'
REPLICATED_LOG_URL = f'_api/log/{STATE_ID}'
REPLICATED_STATE_URL = '_api/replicated-state'
PROTOTYPE_STATE_URL = f'_api/prototype-state/{STATE_ID}'


def create_prototype_state():
    config = {
        'id': STATE_ID,
        'config': {
            'waitForSync': False,
            'writeConcern': 2,
            'softWriteConcern': 2,
            'replicationFactor': 3,
        },
        'properties': {
            "implementation": {"type": "prototype"}
        }
    }
    r = httpx.post(f'{COORD_URL}/{REPLICATED_STATE_URL}', json=config)
    if r.is_success:
        print(r.json())
    else:
        print(r.text)


def insert_entries(entries=None):
    if entries is None:
        size = random.randint(1, 100)
        entries = {f'key{num}': f'value{num}' for num in np.random.randint(1000, size=size)}
    r = httpx.post(f'{COORD_URL}/{PROTOTYPE_STATE_URL}/insert', json=entries, timeout=300)
    if r.is_success:
        print(f'Inserting {len(entries)} entries: {r.json()["result"]}')
    else:
        #print(r.text)
        pass


def remove_entries(entries=None):
    if entries is None:
        size = random.randint(1, 100)
        entries = [f'key{num}' for num in np.random.randint(1000, size=size)]
    r = httpx.request("DELETE", f'{COORD_URL}/{PROTOTYPE_STATE_URL}/multi-remove', json=entries, timeout=300)
    if r.is_success:
        print(f'Removing {len(entries)} entries: {r.json()["result"]}')
    else:
        #print(r.text)
        pass


def chaos():
    while True:
        try:
            if random.randint(0, 1):
                insert_entries()
            else:
                remove_entries()
        except:
            pass


def snapshot():
    r = httpx.get(f'{COORD_URL}/{PROTOTYPE_STATE_URL}/snapshot')
    if r.is_success:
        print(r.json()['result'])
    else:
        print(r.text)


def commit_index(server=None):
    # Returns commit index or server spearhead
    r = httpx.get(f'{COORD_URL}/{REPLICATED_LOG_URL}', timeout=600)
    if r.is_success:
        status = r.json()
        leader = status['result']['participants'][status['result']['leaderId']]
        if server is None:
            return leader['response']['local']['commitIndex']
        else:
            return leader['response']['follower'][server]['spearhead']['index']
    else:
        print(r.text)


def log_tail(server=None):
    index = commit_index(server)
    step = 1
    with tqdm(initial=index) as pbar:
        while True:
            try:
                r = httpx.get(f'{COORD_URL}/{REPLICATED_LOG_URL}/poll?first={index}?limit={step}', timeout=300)
                if r.is_success:
                    '''
                    for entry in r.json()['result']:
                        print(entry['logIndex'])
                    '''
                    pbar.update(step)
                    index += step
                else:
                    pass
                    #print(r.text)
            except:
                pass


def set_leader(new_leader):
    url = f'{COORD_URL}/{REPLICATED_STATE_URL}/{STATE_ID}/leader/{new_leader}'
    r = httpx.post(url, timeout=300)
    if r.is_success:
        print(r.json())
    else:
        print(r.text)


def replace_participant(old, new):
    url = f'{COORD_URL}/{REPLICATED_STATE_URL}/{STATE_ID}/participant/{old}/replace-with/{new}'
    r = httpx.post(url, timeout=300)
    if r.is_success:
        print(r.json())
    else:
        print(r.text)


def get_endpoints():
    url = f'{COORD_URL}/_admin/cluster/health'
    r = httpx.get(url)
    if r.is_success:
        s = r.json()
        prmr = [p for p in s['Health'].keys() if p.startswith('PRMR')]
        return prmr
    else:
        print(r.text)

def replace_all():
    r = httpx.get(f'{COORD_URL}/{PROTOTYPE_STATE_URL}', timeout=600)
    if r.is_success:
        status = r.json()
        participants = list(status['result']['participants'].keys())
    else:
        print(r.text)
        return
    endpoints = get_endpoints()
    mapping = {}
    idx = 0
    for e in endpoints:
        if e not in participants:
            mapping[participants[idx]] = e
            idx += 1
            if idx == len(participants):
                break
    for k, v in mapping.items():
        print(f'Replacing {k} with {v}')
        replace_participant(k, v)


if __name__ == '__main__':
    if sys.argv[1] == 'chaos':
        chaos()
    elif sys.argv[1] == 'log_tail':
        if len(sys.argv) == 3:
            log_tail(sys.argv[2])
        else:
            log_tail()
    #create_prototype_state()
    #insert_entries()
    #snapshot()
    #remove_entries()
    #chaos()
    #print(commit_index())
    #log_tail()
    #replace_all()
