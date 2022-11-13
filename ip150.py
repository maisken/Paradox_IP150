import functools
import hashlib
import json
import logging
import re
import threading
import time

import requests
from bs4 import BeautifulSoup


class Paradox_IP150_Error(Exception):
    pass


class KeepAlive(threading.Thread):

    def __init__(self, ip150url, interval):
        threading.Thread.__init__(self, daemon=True)
        self.ip150url = ip150url
        self.interval = interval
        self.stopped = threading.Event()

    def _one_keepalive(self):
        try:
            requests.get('{}/keep_alive.html'.format(
                self.ip150url), params={'msgid': 1}, verify=False, timeout=(self.interval/2,self.interval))
        except requests.Timeout as t:
            # This keepalive didn't go through. No big deal.
            # We log it and move on; we'll keepalive the next time we're called.
            logging.debug('Keepalive request timed out: {}'.format(t))

    def run(self):
        while not self.stopped.wait(self.interval):
            self._one_keepalive()

    def cancel(self):
        self.stopped.set()


class Paradox_IP150:

    _tables_map = {
        # A map from human readable info about the alarm, to "table" (in fact, array) names used in IP150 software
        #'triggered_alarms': 'tbl_alarmes', # Redundant list of zones with an alarm currently triggered. A zone in alarm will also be reported in the 'tbl_useraccess' table
        #'troubles': 'tbl_troubles', # Could use this list to publish alarm troubles, not required for now
        # The next list provides the status (0=Closed, 1=Open) for each zone
        'zones_status': {
            'name': 'tbl_statuszone',
            'map' : {
                0: 'Closed',
                1: 'Open',
                2: 'In_alarm',
                3: 'Closed_Trouble',
                4: 'Open_Trouble',
                5: 'Closed_Memory',
                6: 'Open_Memory',
                7: 'Bypass',
                8: 'Closed_Trouble2',
                9: 'Open_Trouble2'
            }
        },
        # The next list provides the status (as an integer, 0 for area not enabled) for each supported area
        'areas_status': {
            'name': 'tbl_useraccess',
            'map' : {
                0: 'Unset',
                1: 'Disarmed',
                2: 'Armed',
                3: 'Triggered',
                4: 'Armed_sleep',
                5: 'Armed_stay',
                6: 'Entry_delay',
                7: 'Exit_delay',
                8: 'Ready',
                9: 'Not_ready',
                10: 'Instant'
            }
        }
    }

    _areas_action_map = {
        # Mappring from human readable commands to machine readable
        'Disarm'   : 'd',
        'Arm'      : 'r',
        'Arm_sleep': 'p',
        'Arm_stay' : 's'
    }

    def __init__(self, ip150url):
        self.ip150url = ip150url
        self.logged_in = False
        self._keepalive = None
        self._updates = None
        self._stop_updates = threading.Event()

    def _logged_only(f):
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            if not self.logged_in:
                raise Paradox_IP150_Error(
                    'Not logged in; please use login() first.')
            else:
                return f(self, *args, **kwargs)
        return wrapped

    def _to_8bits(self, s):
        return "".join(map(lambda x: chr(ord(x) % 256), s))

    def _paradox_rc4(self, data, key):
        S, j, out = list(range(256)), 0, []

        # This is not standard RC4
        for i in range(len(key) - 1, -1, -1):
            j = (j + S[i] + ord(key[i])) % 256
            S[i], S[j] = S[j], S[i]

        i = j = 0
        # This is not standard RC4
        for ch in data:
            i = i % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            out.append(ord(ch) ^ S[(S[i] + S[j]) % 256])
            i += 1

        return "".join(map(lambda x: '{0:02x}'.format(x), out)).upper()

    def _prep_cred(self, user, pwd, sess):
        pwd_8bits = self._to_8bits(pwd)
        pwd_md5 = hashlib.md5(pwd_8bits.encode('ascii')).hexdigest().upper()
        spass = pwd_md5 + sess
        return {'p': hashlib.md5(spass.encode('ascii')).hexdigest().upper(),
                'u': self._paradox_rc4(user, spass)}

    def login(self, user, pwd, keep_alive_interval=5.0):
        if self.logged_in:
            raise Paradox_IP150_Error(
                'Already logged in; please use logout() first.')

        # Ask for a login page, to get the 'sess' salt
        lpage = requests.get(
            '{}/login_page.html'.format(self.ip150url), verify=False)

        # Extract the 'sess' salt
        off = lpage.text.find('loginaff')
        if off == -1:
            raise Paradox_IP150_Error(
                'Wrong page fetcehd. Did you connect to the right server and port? Server returned: {}'.format(lpage.text))
        sess = lpage.text[off + 10:off + 26]

        # Compute salted credentials and do the login
        creds = self._prep_cred(user, pwd, sess)
        defpage = requests.get('{}/default.html'.format(
            self.ip150url), params=creds, verify=False)
        if defpage.text.count("top.location.href='login_page.html';") > 0:
            # They're redirecting us to the login page; credentials didn't work
            raise Paradox_IP150_Error(
                'Could not login, wrong credentials provided.')
        # Give enough time to the server to set up.
        time.sleep(3)
        if keep_alive_interval:
            self._keepalive = KeepAlive(self.ip150url, keep_alive_interval)
            self._keepalive.start()
        self.logged_in = True
        logging.info("Successfully logged into the Paradox web interface.")

    @_logged_only
    def logout(self):
        if self._keepalive:
            self._keepalive.cancel()
            self._keepalive.join()
            self._keepalive = None
        if self._updates:
            self._stop_updates.set()
            self._updates = None
        logout = requests.get(
            '{}/logout.html'.format(self.ip150url), verify=False)
        if logout.status_code != 200:
            raise Paradox_IP150_Error('Error logging out')
        self.logged_in = False
        logging.info("Logged out from the Paradox web interface.")

    def _js2array(self, varname, script):
        res = re.search('{} = new Array\((.*?)\);'.format(varname), script)
        res = '[{}]'.format(res.group(1))
        return json.loads(res)

    def _retry_get(self, url, params=None, **kwargs):
        retries = 5
        result = None
        while result == None and retries > 0:
            try:
                result = requests.get(url, params=params, **kwargs)
            except requests.Timeout as t:
                retries = retries-1
                logging.debug('GET request timed out. {} attempts left: {}'.format(retries, t))
        if retries == 0:
            raise Paradox_IP150_Error('GET request permanently timed out.')
        return result

    @_logged_only
    def get_info(self, timeout):
        status_page = self._retry_get(
            '{}/statuslive.html'.format(self.ip150url), verify=False, timeout=(timeout/2,timeout))
        status_parsed = BeautifulSoup(status_page.text, 'html.parser')
        if status_parsed.find('form', attrs={'name': 'statuslive'}) is None:
            raise Paradox_IP150_Error('Could not retrieve status information')
        script = status_parsed.find('script').string
        res = {}
        for table in self._tables_map.keys():
            #Extract the js array for the current "table"
            tmp = self._js2array(self._tables_map[table]['name'], script)
            #Map the extracted machine values to the corresponding human values
            res[table] = [(i, self._tables_map[table]['map'][x]) for i,x in enumerate(tmp, start=1)]
        return res

    def _get_updates(self, on_update, on_error, userdata, interval):
        try:
            prev_state = {}

            while not self._stop_updates.wait(interval):
                updated_state = {}
                cur_state = self.get_info(interval)
                for d1 in cur_state.keys():
                    if d1 in prev_state:
                        for cur_d2, prev_d2 in zip(cur_state[d1], prev_state[d1]):
                            if cur_d2 != prev_d2:
                                if d1 in updated_state:
                                    updated_state[d1].append(cur_d2)
                                else:
                                    updated_state[d1] = [cur_d2]
                    else:
                        updated_state[d1] = cur_state[d1]

                if len(updated_state) > 0:
                    on_update(updated_state, userdata)

                prev_state = cur_state
        except Exception as e:
            if on_error:
                on_error(e, userdata)
        finally:
            self._stop_updates.clear()

    @_logged_only
    def get_updates(self, on_update=None, on_error=None, userdata=None, poll_interval=1.0):
        if not on_update:
            raise Paradox_IP150_Error('The callable on_update must be provided.')
        if poll_interval <= 0.0:
            raise Paradox_IP150_Error('The polling interval must be greater than 0.0 seconds.')
        self._updates = threading.Thread(target=self._get_updates, args=(on_update, on_error, userdata, poll_interval), daemon=True)
        self._updates.start()

    @_logged_only
    def cancel_updates(self):
        if self._updates:
            self._stop_updates.set()
            self._updates = None
        else:
            raise Paradox_IP150_Error('Not currently getting updates. Use get_updates() first.')

    @_logged_only
    def set_area_action(self, area, action):
        if isinstance(area,str):
            area = int(area)
        area = area -1
        if area < 0:
            raise Paradox_IP150_Error('Invalid area provided.')
        if action not in self._areas_action_map:
            raise Paradox_IP150_Error('Invalid action "{}" provided. Valid actions are {}'.format(action, list(self._areas_action_map.keys())))
        action = self._areas_action_map[action]
        act_res = self._retry_get('{}/statuslive.html'.format(self.ip150url), params={'area': '{:02d}'.format(area), 'value': action}, verify=False, timeout=3.0)
        if act_res.status_code != 200:
            raise Paradox_IP150_Error('Error setting the area action')
