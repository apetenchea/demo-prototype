import sys
import httpx
import random
import numpy as np
from tqdm import tqdm
from tabulate import tabulate
from colorama import Fore
import logging
import socket
import json


STATE_ID = 12
COORD_URL = f'http://localhost:8530'
REPLICATED_LOG_URL = f'_api/log/{STATE_ID}'
REPLICATED_STATE_URL = '_api/replicated-state'
PROTOTYPE_STATE_URL = f'_api/prototype-state/{STATE_ID}'

logging.basicConfig(filename='demo-logging.txt',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.ERROR)


def create_prototype_state():
    wc = 2
    rc = 3
    state_type = 'prototype'
    config = {
        'id': STATE_ID,
        'config': {
            'waitForSync': False,
            'writeConcern': wc,
            'softWriteConcern': wc,
            'replicationFactor': rc,
        },
        'properties': {
            "implementation": {"type": state_type}
        }
    }
    r = httpx.post(f'{COORD_URL}/{REPLICATED_STATE_URL}', json=config)
    if r.is_success:
        cols = ['Replicated State', 'ID', 'Write Concern', 'Replication Factor']
        values = [[state_type, STATE_ID, wc, rc]]
        print(tabulate(values, cols, tablefmt='pretty'))
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
        pass


def remove_entries(entries=None):
    if entries is None:
        size = random.randint(1, 100)
        entries = [f'key{num}' for num in np.random.randint(1000, size=size)]
    r = httpx.request("DELETE", f'{COORD_URL}/{PROTOTYPE_STATE_URL}/multi-remove', json=entries, timeout=300)
    if r.is_success:
        print(f'Removing {len(entries)} entries: {r.json()["result"]}')
    else:
        pass


def chaos():
    while True:
        try:
            if random.randint(0, 1):
                insert_entries()
            else:
                remove_entries()
        except KeyboardInterrupt:
            break
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
                    pbar.update(step)
                    index += step
                else:
                    pass
            except KeyboardInterrupt:
                break
            except:
                pass


def get_state_status(leader_id):
    port = get_port(leader_id)
    url = f'http://localhost:{port}/{REPLICATED_STATE_URL}/{STATE_ID}/local-status'
    r = httpx.get(url, timeout=600)
    if r.is_success:
        return r.json()


def parse_with_supervision(status):
    response = status['result']['supervision'].get('response')
    if response is not None:
        term = response['election']['term']
        if term < status['result']['specification']['plan']['currentTerm']['term']:
            print('Trying to contact leader...')
            return
        if 'StatusMessage' in response:
            print(f'{Fore.RED}Election Status: ', response['StatusMessage'], Fore.RESET)
        for k, v in response['election']['details'].items():
            print(f'{k}:', v['message'])
    else:
        print('Trying to contact leader...')


def parse_with_leader(status, leader_id):
    data = {'leader': leader_id, 'commit': {}}
    participants = status['result']['participants']
    sorted_servers = sorted(list(participants.keys()))
    leader = participants[leader_id].get('response')
    if leader is not None:
        followers = leader['follower']
        state_status = get_state_status(leader_id)
        leader_state_status = None
        if state_status is not None:
            leader_state_status = state_status.get('result', {}).get('manager', {}).get('managerState')
            if leader_state_status != 'RecoveryInProgress':
                leader_state_status = None
    else:
        parse_with_supervision(status)
        return
    for k in sorted_servers:
        v = participants[k]
        if v['connection']['errorCode']:
            color = Fore.RED
        elif k == leader_id and leader_state_status:
            color = Fore.CYAN
        else:
            color = Fore.BLUE
        s = color + k + Fore.RESET + ": " + ("leader " if k == leader_id else "follower")
        if v['connection']['errorCode']:
            flags = leader['activeParticipantsConfig']['participants'][k]
            s += " flags="
            s += 'F' if flags['forced'] else '-'
            s += 'Q' if flags['allowedInQuorum'] else '-'
            s += 'L' if flags['allowedAsLeader'] else '-'

        s += '\nStatus '
        if v['connection']['errorCode']:
            s += '(from leader): '
            s += f'spearhead={followers[k]["spearhead"]["index"]} | '
            s += f'{Fore.YELLOW}commit={followers[k]["commitIndex"]}{Fore.RESET} | '
            s += f'term={followers[k]["spearhead"]["term"]}'
            idx = followers[k]["commitIndex"]
        else:
            s += '(from server): '
            s += f'spearhead={v["response"]["local"]["spearhead"]["index"]}'
            s += f' | {Fore.YELLOW}commit={v["response"]["local"]["commitIndex"]}{Fore.RESET}'
            s += f' | term={v["response"]["local"]["spearhead"]["term"]}'
            idx = v["response"]["local"]["commitIndex"]
            #  Not doing log compaction, so there's no need for first index
            #  s += f' | firstIndex={v["response"]["local"]["firstIndex"]}'

        data['commit'][k] = idx

        s += '\nState: '
        if k == leader_id:
            s += f'{v["response"]["lastCommitStatus"]["reason"]}'
            if leader_state_status:
                s += f' | {leader_state_status}'
        else:
            error = followers[k]["lastErrorReason"]["error"]
            s += 'OK' if error == 'None' else error

        print(s)
        print('-' * 56)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('127.0.0.1', 47777))
            sock.sendall(json.dumps(data).encode('utf8'))
    except:
        pass


def get_log_status():
    logger = logging.getLogger('get_log_status')
    r = httpx.get(f'{COORD_URL}/{REPLICATED_LOG_URL}', timeout=600)
    if r.is_error:
        logger.error(r.text)
        return
    return r.json()


def parse_log_info():
    status = get_log_status()
    leader_id = status['result'].get('leaderId')

    if leader_id is not None:
        parse_with_leader(status, leader_id)
    else:
        parse_with_supervision(status)


def unset_leader():
    url = f'{COORD_URL}/{REPLICATED_STATE_URL}/{STATE_ID}/leader'
    r = httpx.delete(url, timeout=300)
    if r.is_error:
        print(r.json())


def set_leader(new_leader):
    url = f'{COORD_URL}/{REPLICATED_STATE_URL}/{STATE_ID}/leader/{new_leader}'
    r = httpx.post(url, timeout=300)
    if r.is_error:
        print(r.json())


def replace_all():
    participants = get_participants()
    unused = get_unused()[-len(participants):]
    print(f'Replacing {participants} with {unused}')
    for i in range(len(participants)):
        replace_participant(participants[i], unused[i])


def replace_participant(old, new):
    url = f'{COORD_URL}/{REPLICATED_STATE_URL}/{STATE_ID}/participant/{old}/replace-with/{new}'
    r = httpx.post(url, timeout=300)
    if r.is_error:
        print(r.text)


def get_leader():
    logger = logging.getLogger('get_leader')
    r = httpx.get(f'{COORD_URL}/{REPLICATED_LOG_URL}', timeout=600)
    if r.is_error:
        logger.error(r.text)
        return
    print(r.json()['result']['leaderId'])


def get_endpoints():
    url = f'{COORD_URL}/_admin/cluster/health'
    r = httpx.get(url)
    if r.is_success:
        s = r.json()
        prmr = {p: v['Endpoint'] for p, v in s['Health'].items() if p.startswith('PRMR')}
        return prmr
    else:
        print(r.text)


def get_participants():
    logger = logging.getLogger('get_participants')
    r = httpx.get(f'{COORD_URL}/{REPLICATED_LOG_URL}', timeout=600)
    if r.is_error:
        logger.error(r.text)
        return
    status = r.json()
    return list(status['result']['participants'].keys())


def get_unused():
    participants = get_participants()
    endpoints = get_endpoints()
    unused = [e for e in endpoints if e not in participants]
    return unused


def get_port(server):
    ep = get_endpoints()
    port = ep[server].split(':')[-1]
    return port


if __name__ == '__main__':
    if sys.argv[1] == 'chaos':
        chaos()
    elif sys.argv[1] == 'get_unused':
        unused = get_unused()
        for p in unused:
            print(p)
    elif sys.argv[1] == 'log_tail':
        if len(sys.argv) == 3:
            log_tail(sys.argv[2])
        else:
            log_tail()
    elif sys.argv[1] == 'get_port':
        print(get_port(sys.argv[2]))
    elif sys.argv[1] == 'replace_participant':
        replace_participant(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'set_leader':
        set_leader(sys.argv[2])
    else:
        locals()[sys.argv[1]]()
