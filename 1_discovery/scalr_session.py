# -*- coding: utf-8 -*-

import json
import requests

from exceptions import ScalrRequestFailure


PAGINATION = 50


def check_response(response):
    response.raise_for_status()
    if not response.json()["success"]:
        try:
            err_msg = response.json()["errorMessage"]
        except KeyError:
            try:
                err_msg = ", ".join([ "{0}: {1}.".format(field, ", ".join(errors)) for field, errors in response.json()["errors"].items()])
            except (TypeError, KeyError):
                err_msg = response.content
        raise ScalrRequestFailure(err_msg)


class ScalrSession(requests.Session):
    def __init__(self, base_url, request_options=None):
        super(ScalrSession, self).__init__()
        self.base_url = base_url
        self.request_options = request_options if request_options is not None else {}

        self.headers["X-Scalr-Token"] = "key"
        self.headers["X-Scalr-Interface"] = "v2"
        self.headers["User-Agent"] = "Scalr Training HTTP Client"

        self.csrf_token = None


    @classmethod
    def from_account(cls, account):
        session = ScalrSession()
        session.login(account["Email"], account["Password"], account["AccountId"])
        return session


    @property
    def user_id(self):
        return self.headers["X-Scalr-UserId"]


    @user_id.setter
    def user_id(self, value):
        self.headers["X-Scalr-UserId"] = value


    @property
    def env_id(self):
        return self.headers["X-Scalr-EnvId"]


    @env_id.setter
    def env_id(self, value):
        self.headers["X-Scalr-EnvId"] = value


    def prepare_request(self, request):
        if request.method in ("POST",):
            kwargs = request.data
        elif request.method in ("GET",):
            kwargs = request.params
        else:
            kwargs = {}

        if self.csrf_token is not None:
            kwargs["X-Requested-Token"] = self.csrf_token

        request.url = "".join([self.base_url, request.url])
        return super(ScalrSession, self).prepare_request(request)


    def request(self, *args, **kwargs):
        request_kwargs = {}
        request_kwargs.update(kwargs)
        request_kwargs.update(self.request_options)
        res = super(ScalrSession, self).request(*args, **request_kwargs)
        check_response(res)
        return res


    def _get_list_from_url(self, list_url, per_page=PAGINATION, extra_params=None):
        if extra_params is None:
            extra_params = {}
        results = []
        page = 0

        while 1:
            page += 1
            params = {
                "page": page,                    # 1-indexed
                "start": per_page * (page - 1),  # 0-indexed
                "limit": per_page,
            }
            params.update(extra_params)

            res = self.get(list_url, params=params)
            json = res.json()

            results.extend(json["data"])
            if len(results) == int(json["total"]):
                break

        return results

    ###################
    # Auth Management #
    ###################

    def login(self, username, password, account_id=None, tfa=None):
        data = {"scalrLogin": username, "scalrPass": password, "scalrKeepSession": "on"}
        if account_id is not None:
            data.update({"accountId": account_id})
        if tfa is not None:
            data.update({"tfaGglCode": tfa})

        res = self.post("/guest/xLogin", data)
        self.csrf_token = res.json().get("specialToken")
        self._load_context()

        return res


    def _get_context(self):
        return self.post("/guest/xGetContext").json()


    def _load_context(self):
        ctx = self._get_context()

        user = ctx["user"]
        self.env_id = str(user["envId"])
        self.user_id = str(user["userId"])


    def list_environments(self):
        ctx = self._get_context()
        return ctx["environments"]


    def set_environment(self, env_id):
        res = self.post("/core/xChangeEnvironment", data={
            "envId": env_id
        })
        self.env_id = env_id
        self._load_context()


    ###################
    # User Management #
    ###################

    def list_accounts(self, per_page=PAGINATION):
        return self._get_list_from_url("/admin/accounts/xListAccounts", per_page)


    def create_account(self, name, email, password):
        res = self.post("/admin/accounts/xSave", {"name": name, "ownerEmail": email, "ownerPassword": password,
                                                  "limitEnv": "-1", "limitUsers": "-1", "limitFarms": "-1",
                                                  "limitServers": "-1"})
        return res


    def admin_login_as(self, account_id):
        self.post("/admin/accounts/xLoginAs", data={
            "accountId": account_id
        })
        self.env_id = None
        self.user_id = None
        self._load_context()


    #####################
    # Discovery manager #
    #####################

    def get_servers_for_import(self, location):
        return self._get_list_from_url('/discoverymanager/servers/xList',
                                       extra_params={'platform': 'ec2', 'cloudLocation': location})

