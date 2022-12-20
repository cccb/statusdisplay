# Copyright 2020, 2021, 2022 Dominik George <dominik.george@teckids.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ntptime
import re
import urequests

_MYTRIX_MYNIT_SCHEMA = {
    "homeserver": ("URL of Matrix homeserver", "str", None, "", "from mytrix import _mytrix_mynit_update; _mytrix_mynit_update"),
    "matrix_id": ("Matrix ID", "str", None, "", "from mytrix import _mytrix_mynit_update; _mytrix_mynit_update"),
    "password": ("Password", "str", None, "", "from mytrix import _mytrix_mynit_update; _mytrix_mynit_update"),
    "access_token": ("Access token", "str", None, "", "from mytrix import _mytrix_mynit_update; _mytrix_mynit_update"),
}


class Matrix:
    """Implements Matrix client functionality and state keeping"""

    sync_limit = 1

    def __init__(self, homeserver=None, matrix_id=None, access_token=None, txn_id=None):
        """Configure the Matrix client.

        The arguments homeserver, matrix_id and access_token configure access to the Matrix network.
        See the Matrix documentation for details.

        The txn_id argument is optional and takes the transaction id to start with. If left out,
        if defaults to the current UNIX timestamp, retrieved by an NTP request. For details on transaction
        IDs, see the Matrix documentation.
        """
        if "mynit" in locals():
            mynit = locals()["mynit"]
            mynit.register("matrix", "Matrix", _MYTRIX_MYNIT_SCHEMA)

            if (homeserver, matrix_id, access_token) != (None, None, None):
                raise TypeError("No arguments must be passed if mynit is used")
            self._mynit_update()
        else:
            self.homeserver = homeserver
            self.matrix_id = matrix_id
            self.access_token = access_token

        if not self.homeserver or not self.matrix_id or not self.access_token:
            raise TypeError("homeserver, matrix_id and access_token must be set")

        if txn_id is None:
            self._txn_id = ntptime.time()
        else:
            self._txn_id = txn_id

        self._from_cache = {}

    def _mynit_update(self):
        mynit = locals()["mynit"]
        self.homeserver = mynit["matrix"]["homeserver"]
        self.matrix_id = mynit["matrix"]["matrix_id"]
        self.access_token = mynit["matrix"]["access_token"]

        if self.matrix_id and mynit["matrix"]["password"] and not self.access_token:
            self.login(self.matrix_id, mynit["matrix"]["password"])

    def _request(self, method, endpoint, query_data=None, json_data=None, unauth=False):
        """Send an HTTP request using urequests."""
        url = "%s/_matrix/client%s" % (self.homeserver, endpoint)

        if query_data:
            qs = "&".join(["%s=%s" % (key_, value) for key_, value in query_data.items()])
            url = "%s?%s" % (url, qs)

        headers = {}
        if not unauth:
            headers["Authorization"] = "Bearer %s" % (self.access_token,)

        res = method(url, json=json_data, headers=headers)
        try:
            data = res.json()
        except:
            data = {}
        if 200 <= res.status_code < 300:
            return data
        else:
            raise RuntimeError(res.reason.decode() + ":" + str(data))

    def _put(self, endpoint, query_data=None, json_data=None, unauth=False):
        """Send a PUT request using urequests."""
        return self._request(urequests.put, endpoint, query_data, json_data, unauth)

    def _post(self, endpoint, query_data=None, json_data=None, unauth=False):
        """Send a POST request using urequests."""
        return self._request(urequests.post, endpoint, query_data, json_data, unauth)

    def _get(self, endpoint, query_data=None, unauth=False):
        """Send a GET request using urequests."""
        return self._request(urequests.get, endpoint, query_data, unauth)

    @property
    def txn_id(self):
        txn_id_cur = self._txn_id
        self._txn_id += 1
        return txn_id_cur

    def login(self, username, password):
        """Login to homeserver using username and password."""
        endpoint = "/r0/login"
        json_data = {"user": username, "password": password, "type": "m.login.password"}

        data = self._post(endpoint, json_data=json_data, unauth=True)

        if "access_token" in data:
            self.access_token = data["access_token"]
        else:
            raise RuntimeError("Login failed")

        if "mynit" in locals():
            mynit = locals()["mynit"]
            mynit["matrix"]["access_token"] = self.access_token

    def send_room_event(self, room, type_, content):
        """Send and arbitrary event to a room."""
        endpoint = "/r0/rooms/%s/send/%s/%s" % (room, type_, self.txn_id)

        return self._put(endpoint, json_data=content)

    def join_room(self, room):
        """Join a room using its ID."""
        endpoint = "/r0/rooms/%s/join" % (room,)

        return self._post(endpoint)

    def set_displayname(self, nick):
        """Set the account's display name."""
        endpoint = "/r0/profile/%s/displayname" % (self.matrix_id,)
        content = {"displayname": nick}

        self._put(endpoint, json_data=content)

    def set_avatar(self, avatar_url):
        """Set the account's avatar by MXC URL."""
        endpoint = "/r0/profile/%s/avatar_url" % (self.matrix_id,)
        content = {"avatar_url": avatar_url}

        self._put(endpoint, json_data=content)

    def send_room_message(self, room, text, msgtype="m.text"):
        """Send a message event to a room."""
        content = {"msgtype": "m.text", "body": text}

        return self.send_room_event(room, "m.room.message", content)

    def send_dm_message(self, mxid, text, msgtype="m.text"):
        """Send a message event to a DM room, discovering or creating it beforehand."""
        room = self.get_dm_room(mxid)
        return self.send_room_message(room, text, msgtype)

    def get_room_messages(self, room, from_=None, dir_="f", limit=None):
        """Get message events for a room.

        The from_ argumenttakes a token defining from which event to start fetching. Normally, it
        can be left out. In that case, the first call will fetch an empty result. This, and all
        subsequent calls, will store the last token received in a cache, which will be used on the
        next call. Effectively, calling this method without a from_ argument will always yield the
        next events since the last call.

        The limit_ argument defaults to the sync_limit attribute of the Matrix instance, which by
        default is 1. This is to not get out-of-memory conditions if some events are big.

        For all other arguments, see the Matrix documentation.
        """
        if limit is None:
            limit = self.sync_limit
        if from_ is None:
            from_ = self._from_cache.get(room, None)

        endpoint = "/r0/rooms/%s/messages" % (room,)

        query_data = {
            "dir": dir_,
            "limit": str(limit),
        }
        if from_:
            query_data["from"] = str(from_)

        data = self._get(endpoint, query_data)

        if "end" in data:
            self._from_cache[room] = data["end"]
        elif "start" in data:
            self._from_cache[room] = data["start"]

        return data

    def get_dm_messages(self, mxid, from_=None, dir_="f", limit=None):
        """Get messages in a DM room, discovering or creating it beforehand."""
        room = self.get_dm_room(mxid)
        return self.get_room_messages(room, from_, dir_, limit)

    def react_room_messages(self, room, cases, regex=False):
        """Get room messages and trigger callbacks.

        The cases argument takes a dictionary mapping strings or compiled regexs to callables.
        All received messages are compared to the keys, and on match, the respective callable
        is called.

        The callback is passed the matching message for string matches, or the list of matched
        groups for regex matches, and the full event that triggered the match.

        The get_room_messages method is called with default values, resulting in this method always
        reacting to new messages since its last call.

        The method returns a list of all matched messages.
        """
        data = self.get_room_messages(room)
        matches = []

        for event in data.get("chunk", []):
            if event["type"] == "m.room.message" and event["content"]["msgtype"] == "m.text":
                message = event["content"]["body"]
                for key_, func in cases.items():
                    if regex:
                        finds = re.search(key_, message)
                        if finds:
                            matches.append(message)
                            func(finds, event)
                            break
                    else:
                        if message.lower().strip() == key_.lower().strip():
                            matches.append(message)
                            func(message, event)
                            break

        return matches

    def react_dm_messages(self, mxid, cases):
        """Get DM messages and trigger callbacks."""
        room = self.get_dm_room(mxid)
        return self.react_room_messages(room, cases)

    def get_account_data(self, type_):
        """Get the account data of the given type."""
        endpoint = "/r0/user/%s/account_data/%s" % (self.matrix_id, type_)

        data = self._get(endpoint)
        return data

    def set_account_data(self, type_, content):
        """Set the account data of the given type."""
        endpoint = "/r0/user/%s/account_data/%s" % (self.matrix_id, type_)
        res = self._put(endpoint, json_data=content)

    def _create_dm_room(self, mxid, dm_rooms=None):
        """Create a DM chat with the given matrix ID."""
        endpoint = "/r0/createRoom"
        content = {"preset": "trusted_private_chat", "invite": [mxid], "is_direct": True}

        res = self._post(endpoint, json=content)
        room_id = res["room_id"]

        if dm_rooms is None:
            dm_rooms = self.get_account_data("m.direct")
        dm_rooms.setdefault(mxid, []).append(room_id)
        self.set_account_data("m.direct", dm_rooms)

        return room_id

    def get_dm_room(self, mxid):
        """Get the (first) DM room for a target Matrix ID.

        This will try to look up the DM room in the acocunt state. If a DM room for the
        desired user is found, its room ID is returned; if not, a new DM room is created.
        """
        dm_rooms = self.get_account_data("m.direct")
        if mxid in dm_rooms and len(dm_rooms[mxid]) > 0:
            return dm_rooms[mxid][0]

        return self._create_dm_room(mxid, dm_rooms)


_mytrix_instances = []


def _mytrix_mynit_update():
    for i in _mytrix_instances:
        i._mynit_update()
