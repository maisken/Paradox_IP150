import hashlib
import requests
import time
import threading
from bs4 import BeautifulSoup
import re
import json

class Paradox_IP150_Login(Exception):
    pass

class KeepAlive(threading.Thread):
    def __init__(self, ip150url, interval=5.0):
        threading.Thread.__init__(self, daemon=True)
        self.ip150url = ip150url
        self.interval = interval
        self.stopped = threading.Event()

    def _one_keepalive(self):
        requests.get('{}/keep_alive.html'.format(self.ip150url), params = {'msgid': 1})

    def run(self):
        while not self.stopped.wait(self.interval):
            self._one_keepalive()

    def cancel(self):
        self.stopped.set()

class Paradox_IP150:

    _varmap = {
        'alarms': 'tbl_alarmes',
        'troubles': 'tbl_troubles',
        'status_zone': 'tbl_statuszone'
    }

    def __init__(self, addr, port=80, method='http'):
        self.ip150url = '{}://{}:{}'.format(method,addr,port)
        self.logged_in = False
        self._keepalive = None

    def _to_8bits(self, s):
        return "".join(map(lambda x: chr(ord(x) % 256), s))

    def _paradox_rc4(self, data, key):
        S, j, out = list(range(256)), 0, []

        # This is not standard RC4
        for i in range(len(key)-1,-1,-1):
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
            
        return "".join(map(lambda x: '{0:02x}'.format(x),out)).upper()

    def _prep_cred(self, user, pwd, sess):
        pwd_8bits = self._to_8bits(pwd)
        pwd_md5 = hashlib.md5(pwd_8bits.encode('ascii')).hexdigest().upper()
        spass = pwd_md5 + sess
        return {'p': hashlib.md5(spass.encode('ascii')).hexdigest().upper(),
                'u': self._paradox_rc4(user, spass)}

    def login(self, user, pwd):
        if self.logged_in:
            raise Paradox_IP150_Login('Already logged in; please use logout() first.')

        # Ask for a login page, to get the 'sess' salt
        lpage = requests.get('{}/login_page.html'.format(self.ip150url), verify=False)
        
        # Extract the 'sess' salt
        off = lpage.text.find('loginaff')
        if off == -1:
            raise Paradox_IP150_Login('Wrong page fetcehd. Did you connect to the right server and port? Server returned: {}'.format(lpage.text))
        sess = lpage.text[off+10:off+26]
        
        # Compute salted credentials and do the login
        creds = self._prep_cred(user,pwd,sess)
        defpage = requests.get('{}/default.html'.format(self.ip150url), params=creds, verify=False)
        if defpage.text.count("top.location.href='login_page.html';") > 0:
            # They're redirecting us to the login page; credentials didn't work
            raise Paradox_IP150_Login('Could not login, wrong credentials provided.')
        # Give enough time to the server to set up.
        time.sleep(3)
        self._keepalive = KeepAlive(self.ip150url)
        self._keepalive.start()
        self.logged_in = True

    def logout(self):
        if not self.logged_in:
            raise Paradox_IP150_Login('Not logged in; please use login() first.')

        self._keepalive.cancel()
        logout = requests.get('{}/logout.html'.format(self.ip150url), verify=False)
        if logout.status_code != 200:
            raise Paradox_IP150_Login('Error logging out')
        self.logged_in = False

    def _js2array(self, varname, script):
        res = re.search('{} = new Array\((.*?)\);'.format(varname),script)
        res = '[{}]'.format(res.group(1))
        return json.loads(res)

    def get_info(self):
        status_page = requests.get('{}/statuslive.html'.format(self.ip150url), verify=False)
        status_parsed = BeautifulSoup(status_page.text, 'html.parser')
        if status_parsed.find('form',attrs={'name':'statuslive'}) == None:
            raise Paradox_IP150_Login('Could not retrieve status information')
        script = status_parsed.find('script').string
        res = {}
        for varname in self._varmap.keys():
            res[varname] = self._js2array(self._varmap[varname],script)
        return res