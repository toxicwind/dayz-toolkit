import logging
from typing import Any

import httpx

log = logging.getLogger("dayz-discord-ops.nitrado")


class NitradoAPIClient:
    BASE_URL = "https://api.nitrado.net"

    def __init__(self, token: str):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            try:
                res = await client.request(method, f"{self.BASE_URL}{path}", **kwargs)
                res.raise_for_status()
                return res.json()
            except Exception as e:
                log.error(f"Nitrado API {method} {path} failed: {e}")
                return {"status": "error", "message": str(e)}

    async def get_services(self):
        """Get list of services (servers)"""
        return await self._request("GET", "/services")

    async def get_gameserver_details(self, service_id: int):
        return await self._request("GET", f"/services/{service_id}/gameservers")

    async def get_logs_list(self, service_id: int):
        """Returns the curated list of log files from gameserver details"""
        data = await self.get_gameserver_details(service_id)
        if data.get("status") == "success":
            return data.get("data", {}).get("gameserver", {}).get("game_specific", {}).get("log_files", [])
        return []

    async def download_file(self, service_id: int, file_path: str) -> str | None:
        """Downloads a file via the File Server API"""
        # Step 1: Get download token/URL
        res = await self._request(
            "GET", f"/services/{service_id}/gameservers/file_server/download", params={"file": file_path}
        )
        if res.get("status") == "success":
            download_url = res.get("data", {}).get("token", {}).get("url")
            if download_url:
                try:
                    async with httpx.AsyncClient() as client:
                        file_res = await client.get(download_url)
                        file_res.raise_for_status()
                        return file_res.text
                except Exception as e:
                    log.error(f"Failed to download from {download_url}: {e}")
        return None

    async def get_service_logs(self, service_id: int, page: int = 1) -> dict | None:
        """Get service event logs (restarts, status changes, etc)"""
        res = await self._request("GET", f"/services/{service_id}/logs", params={"page": page})
        if res.get("status") == "success":
            return res.get("data", {})
        return None

    async def get_settings(self, service_id: int):
        # This method was a wrapper for get_gameserver_details in the original sync version
        # Keeping it for compatibility if other methods rely on its name, but it's redundant.
        return await self.get_gameserver_details(service_id)

    async def update_setting(self, service_id: int, category: str, key: str, value: str):
        # Nitrado API expects form-data for settings
        return await self._request(
            "POST",
            f"/services/{service_id}/gameservers/settings",
            data={"category": category, "key": key, "value": value},
        )

    async def ban_player(self, service_id: int, gamertag: str):
        # Fetch current bans first
        data = await self.get_gameserver_details(service_id)  # Changed from get_settings to get_gameserver_details
        if not data or data.get("status") != "success":
            return {"status": "error", "message": "Failed to fetch current settings"}

        try:
            current_bans = data["data"]["gameserver"]["settings"]["general"]["bans"] or ""
            if gamertag in current_bans:
                return {"status": "success", "message": "Player already banned"}

            new_bans = f"{current_bans}\r\n{gamertag}".strip()
            return await self.update_setting(service_id, "general", "bans", new_bans)
        except KeyError:
            return {"status": "error", "message": "Could not parse current bans from settings"}

    async def restart_server(self, service_id: int, message: str = "Restarting..."):
        return await self._request(
            "POST",
            f"/services/{service_id}/gameservers/restart",
            json={"restart_message": message, "message": message},
        )

    async def stop_server(self, service_id: int, message: str = "Stopping..."):
        return await self._request("POST", f"/services/{service_id}/gameservers/stop", json={"message": message})

    async def get_status(self, service_id: int):
        """Returns the current status of the gameserver (e.g. 'started', 'stopped')"""
        data = await self.get_gameserver_details(service_id)
        if data.get("status") == "success":
            return data.get("data", {}).get("gameserver", {}).get("status")
        return "unknown"

    async def get_websocket_token(self, service_id: int) -> str | None:
        """Get WebSocket token for real-time console access"""
        data = await self.get_gameserver_details(service_id)
        if data.get("status") == "success":
            return data.get("data", {}).get("gameserver", {}).get("websocket_token")
        return None
