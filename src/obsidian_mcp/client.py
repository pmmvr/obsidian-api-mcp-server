import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


class ObsidianClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        headers = kwargs.pop("headers", {})
        headers.update(self.headers)
        
        async with httpx.AsyncClient(verify=False) as client:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = await client.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                raise Exception("Obsidian API requires authentication. Please set OBSIDIAN_API_KEY environment variable.")
            response.raise_for_status()
            return response.json()
    
    async def search_simple(self, query: str, context_length: int = 100) -> List[Dict[str, Any]]:
        return await self._request(
            "POST", 
            "/search/simple/", 
            params={"query": query, "contextLength": context_length}
        )
    
    async def get_note_metadata(self, path: str) -> Dict[str, Any]:
        encoded_path = quote(path, safe='/')
        return await self._request(
            "GET", 
            f"/vault/{encoded_path}",
            headers={"Accept": "application/vnd.olrapi.note+json"}
        )
    
    async def list_directory(self, path: str = "") -> List[str]:
        if path:
            # Just URL encode the path and try it directly
            encoded_path = quote(path, safe='/')
            endpoint = f"/vault/{encoded_path}/"
        else:
            endpoint = "/vault/"
        
        result = await self._request("GET", endpoint)
        return result.get("files", [])

    async def search_advanced(self, jsonlogic_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute advanced search using JsonLogic query format."""
        return await self._request(
            "POST",
            "/search/",
            json=jsonlogic_query,
            headers={"Content-Type": "application/vnd.olrapi.jsonlogic+json"}
        )
    
    async def browse_vault(self, base_path: str = "", include_files: bool = False, recursive: bool = False, max_depth: int = 10) -> List[str]:
        """Browse vault structure with flexible filtering options."""
        if not recursive:
            all_items = await self.list_directory(base_path)
            if not include_files:
                # Filter to only show directories (items ending with '/')
                return [item for item in all_items if item.endswith('/')]
            return all_items
        
        all_items = []
        
        async def _recursive_list(current_path: str, depth: int):
            if depth > max_depth:
                return
                
            try:
                items = await self.list_directory(current_path)
                for item in items:
                    if current_path:
                        full_path = f"{current_path}/{item}"
                    else:
                        full_path = item
                    
                    # Apply file filtering
                    if include_files or item.endswith('/'):
                        all_items.append(full_path)
                    
                    # If it's a directory, recurse into it
                    if item.endswith('/'):
                        await _recursive_list(full_path.rstrip('/'), depth + 1)
            except Exception:
                # Skip directories we can't access
                pass
        
        await _recursive_list(base_path, 0)
        return all_items
    
    async def list_all_files(self, base_path: str = "", max_depth: int = 10, max_files: int = 5000) -> List[str]:
        """Recursively list all files in the vault with safety limits."""
        all_files = []
        
        async def _recursive_list(current_path: str, depth: int):
            if depth > max_depth or len(all_files) >= max_files:
                return
                
            try:
                files = await self.list_directory(current_path)
                for file in files:
                    if len(all_files) >= max_files:
                        return
                        
                    if current_path:
                        full_path = f"{current_path}/{file.rstrip('/')}"
                    else:
                        full_path = file.rstrip('/')
                    
                    if file.endswith('/'):
                        # It's a directory, recurse into it
                        await _recursive_list(full_path, depth + 1)
                    else:
                        # It's a file, add it to our list
                        all_files.append(full_path)
            except Exception:
                # Skip directories we can't access
                pass
        
        await _recursive_list(base_path, 0)
        return all_files


def create_client() -> ObsidianClient:
    base_url = os.getenv("OBSIDIAN_API_URL", "https://localhost:27124")
    api_key = os.getenv("OBSIDIAN_API_KEY")
    return ObsidianClient(base_url, api_key)