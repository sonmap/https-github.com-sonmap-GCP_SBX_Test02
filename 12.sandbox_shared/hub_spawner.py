"""Injected into the group Hub by the shared sandbox Helm values."""
import asyncio
import base64
import hashlib
import json
import os
import uuid
from urllib.parse import urlparse

from jupyterhub.spawner import Spawner
from kubernetes_asyncio import client, config
from oauthenticator.generic import GenericOAuthenticator
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest


class SharedTaskSpawner(Spawner):
    def slot(self):
        if not self.name:
            raise RuntimeError("Start a named server using the approved task name")
        members = SHARED_TASKS.get(self.name, [])
        if self.user.name not in members:
            raise RuntimeError("This account is not approved for the requested task")
        return members.index(self.user.name)

    @property
    def host(self):
        return f"notebook.{self.name}.svc.cluster.local"

    async def configure(self, slot, data):
        config.load_incluster_config()
        async with client.ApiClient() as api:
            await client.CoreV1Api(api).patch_namespaced_secret(
                "notebook-session-" + hashlib.sha256(SHARED_TASKS[self.name][slot].encode()).hexdigest()[:24],
                self.name, {"data": {"session.json": data}},
                _content_type="application/merge-patch+json",
            )

    async def status(self, slot):
        response = await AsyncHTTPClient().fetch(
            HTTPRequest(f"http://{self.host}:{9000 + slot}/", request_timeout=3),
            raise_error=False,
        )
        return response.body.decode() if response.code == 200 else None

    async def start(self):
        slot = self.slot()
        port = 8888 + slot
        revision = uuid.uuid4().hex
        # Select JupyterHub fields only. Hub process variables and Okta secrets
        # are never written into notebook session Secrets.
        env = {
            key: value for key, value in self.get_env().items()
            if key.startswith("JUPYTERHUB_")
        }
        # get_env uses the spawner's server address for this value.
        env["JUPYTERHUB_SERVICE_URL"] = f"http://0.0.0.0:{port}" + env["JUPYTERHUB_SERVICE_PREFIX"]
        data = base64.b64encode(json.dumps({"revision": revision, "env": env}).encode()).decode()
        await self.configure(slot, data)
        try:
            deadline = asyncio.get_running_loop().time() + 240
            while asyncio.get_running_loop().time() < deadline:
                try:
                    if await self.status(slot) == revision:
                        return self.host, port
                except (OSError, HTTPClientError):
                    pass
                await asyncio.sleep(2)
            raise RuntimeError("Notebook slot did not start. Check the task Deployment and slot logs.")
        except (Exception, asyncio.CancelledError):
            await self.configure(slot, None)
            raise

    async def stop(self, now=False):
        await self.configure(self.slot(), None)

    async def poll(self):
        try:
            return None if await self.status(self.slot()) else 1
        except (OSError, RuntimeError, HTTPClientError):
            return 1


issuer = OKTA_ISSUER.rstrip("/")
if not urlparse(issuer).path:
    issuer += "/oauth2"
c.JupyterHub.spawner_class = SharedTaskSpawner
c.JupyterHub.authenticator_class = GenericOAuthenticator
c.JupyterHub.allow_named_servers = True
c.JupyterHub.hub_connect_url = f"http://hub.{GROUP_NAMESPACE}.svc.cluster.local:8081"
c.Spawner.start_timeout = 300
c.Spawner.http_timeout = 60
c.Authenticator.allow_all = False
c.Authenticator.allow_existing_users = False
c.Authenticator.allowed_users = {member for members in SHARED_TASKS.values() for member in members}
c.GenericOAuthenticator.client_id = os.environ["SHARED_OKTA_CLIENT_ID"]
c.GenericOAuthenticator.client_secret = os.environ["SHARED_OKTA_CLIENT_SECRET"]
c.GenericOAuthenticator.authorize_url = f"{issuer}/v1/authorize"
c.GenericOAuthenticator.token_url = f"{issuer}/v1/token"
c.GenericOAuthenticator.userdata_url = f"{issuer}/v1/userinfo"
c.GenericOAuthenticator.username_claim = "email"
c.GenericOAuthenticator.scope = ["openid", "profile", "email"]
c.GenericOAuthenticator.oauth_callback_url = f"https://{GROUP_DOMAIN}/hub/oauth_callback"
c.GenericOAuthenticator.enable_pkce = True
