from requests import PreparedRequest, Request, Session
from typing import ClassVar

import attr, logging, re, time

LOG = logging.getLogger('HvSession')


@attr.s(auto_attribs=True)
class HvCookies:
    ipb_member_id: str
    ipb_pass_hash: str

@attr.s(auto_attribs=True)
class HvCredentials:
    username: str
    password: str

@attr.s(auto_attribs=True)
class HvSession:
    """
    One of the following must be supplied to the constructor:
        -> cookies: HvCookies
        -> credentials: HvCredentials
            -> this may not work if captchas are enabled for your account / ip
    """

    # class vars
    HV_LINK: ClassVar[str] = "https://hentaiverse.org"
    LOGIN_LINK: ClassVar[str] = "https://forums.e-hentai.org/index.php?act=Login&CODE=01"
    RATE_LIMIT: ClassVar[float] = 1 # seconds btwn requests

    # kwargs for __init__
    cookies: HvCookies = None
    credentials: HvCredentials = None
    session: Session = attr.ib(default=attr.Factory(Session))

    # instance attrs
    did_login: bool = attr.ib(default=False, init=False)
    ign: str = attr.ib(default=None, init=False)

    _last_sent: float = attr.ib(default=0, init=False)
    _is_prepping: bool = attr.ib(default=False, init=False) # avoid recursion when calling _prep_truck
    _seen_main: bool = attr.ib(default=False, init=False) # visited the main hv page at least once
    _seen_main_alt: bool = attr.ib(default=False, init=False)
    _seen_isk: bool = attr.ib(default=False, init=False)
    _seen_isk_alt: bool = attr.ib(default=False, init=False)

    def __attrs_post_init__(self):
        assert any(x is not None for x in [self.cookies, self.credentials]), 'No credentials or cookies (recommended) was supplied to the HvSession constructor.'
        self.login()

    def login(self):
        self._delay_request()
        self._login()

        self.did_login = True
        self._seen_main = False
        self._seen_main_alt = False
        self._seen_isk = False
        self._seen_isk_alt = False

        return self

    def get(self, url: str, encoding='utf-8', **kwargs):
        resp = self.send('get', url, **kwargs)
        if encoding: resp.encoding = encoding

        return resp

    def post(self, url: str, encoding='utf-8', **kwargs):
        resp = self.send('post', url, **kwargs)
        if encoding: resp.encoding = encoding

        return resp

    def send(self, method: str, url: str, **kwargs):
        req = self._prepare_request(method=method, url=url, **kwargs)
        resp = self.session.send(req)
        # LOG.debug(f'response {req.url} {resp.text}')
        return resp

    def _prepare_request(self, method: str, url: str, **kwargs):
        self._prep_truck(url)
        self._delay_request()
        LOG.debug(f'{method} -- {url} -- {kwargs}')

        req = Request(method, url, **kwargs)
        req = self.session.prepare_request(req)
        return req

    def _login(self):
        if self.credentials:
            LOG.debug('Logging into HV via credentials...')

            payload = dict(
                CookieDate=1,
                b='d',
                bt=6,
                UserName=self.credentials.username,
                PassWord=self.credentials.password,
                ipb_login_submit="Login!",
            )

            resp = self.session.post(self.LOGIN_LINK, data=payload)
            assert "You are now logged in as:" in resp.text, 'Login via username / password failed. Possibly because a captcha was required. Maybe try a HvCookies instance instead?'

            ign = re.search("You are now logged in as: (.*?)<br", resp.text)
            self.ign = ign.group(1)
            LOG.info(f'Logged in as {ign}')
        elif self.cookies:
            LOG.debug('Logging into HV via cookies...')

            self.session.cookies.set('ipb_member_id', self.cookies.ipb_member_id, domain='.e-hentai.org')
            self.session.cookies.set('ipb_pass_hash', self.cookies.ipb_pass_hash, domain='.e-hentai.org')

    def _delay_request(self):
        elapsed = time.time() - self._last_sent

        if elapsed < self.RATE_LIMIT:
            delay = self.RATE_LIMIT - elapsed
            time.sleep(delay)

        self._last_sent = time.time()
        return

    # visit hv page at least once after login to set cookies or something
    def _prep_truck(self, url: str):
        is_alt = 'http://alt' in url

        if not self._is_prepping:
            self._is_prepping = True

            if '/isekai/' in url:
                if is_alt and not self._seen_isk_alt:
                        LOG.debug(f'Doing first alt.isekai visit')
                        self._seen_isk_alt = True
                        self.get('http://alt.hentaiverse.org/isekai/')
                elif not is_alt and not self._seen_isk:
                    LOG.debug(f'Doing first isekai visit')
                    self._seen_isk = True
                    self.get('https://hentaiverse.org/isekai/')
                    
            elif not self._seen_main:
                if is_alt and not self._seen_main_alt:
                    LOG.debug(f'Doing first main.alt visit')
                    self._seen_main_alt = True
                    self.get('http://alt.hentaiverse.org/')
                elif not is_alt and not self._seen_main:
                    LOG.debug(f'Doing first main visit')
                    self._seen_main = True
                    self.get('https://hentaiverse.org/')
            
            self._is_prepping = False