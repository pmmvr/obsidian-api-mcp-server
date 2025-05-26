import json
from typing import Any, Dict, Optional, Union, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from obsidian_mcp.client import create_client
from obsidian_mcp.search import SearchProcessor

mcp = FastMCP("obsidian-mcp")
client = create_client()
search_processor = SearchProcessor(client)

@mcp.tool(
    annotations={
        "title": "Search Obsidian Vault",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
async def search_vault(
    query: Optional[str] = None,
    query_type: str = "text",
    search_in_path: Optional[str] = None,
    title_contains: Optional[Any] = None,
    title_match_mode: str = "any",
    tag: Optional[Any] = None,
    tag_match_mode: str = "any",
    context_length: int = 100,
    include_content: bool = False,
    modified_since: Optional[str] = None,
    modified_until: Optional[str] = None,
    created_since: Optional[str] = None,
    created_until: Optional[str] = None,
    page_size: int = 50,
    page: int = 1,
    max_matches_per_file: int = 5
) -> Dict[str, Any]:
    """
    Search Obsidian vault for notes matching criteria.
    
    Args:
        query: Text or regex pattern to search for
        query_type: "text" or "regex" 
        search_in_path: Limit search to specific folder
        title_contains: Filter by title (string or array)
        title_match_mode: "any" or "all" for multiple title terms
        tag: Filter by tag (string, array, or JSON string like title_contains)
        tag_match_mode: "any" or "all" for multiple tag terms
        context_length: Characters of context around matches
        include_content: Return full note content
        modified_since/until: Filter by modification date (YYYY-MM-DD)
        created_since/until: Filter by creation date (YYYY-MM-DD)
        page_size/page: Pagination controls
        max_matches_per_file: Limit matches per file
    """
    parsed_title_contains = title_contains
    if title_contains:
        if isinstance(title_contains, list):
            parsed_title_contains = title_contains
        # Handle title_contains if JSON string representation of list
        elif isinstance(title_contains, str) and title_contains.strip().startswith('['):
            try:
                parsed_title_contains = json.loads(title_contains)
            except json.JSONDecodeError:
                pass
    
    # Handle tag in multiple formats (same logic as title_contains)
    parsed_tag = tag
    if tag:
        if isinstance(tag, list):
            parsed_tag = tag
        elif isinstance(tag, str) and tag.strip().startswith('['):
            try:
                parsed_tag = json.loads(tag)
            except json.JSONDecodeError:
                pass
    
    return await search_processor.search(
        query=query,
        query_type=query_type,
        search_in_path=search_in_path,
        title_contains=parsed_title_contains,
        title_match_mode=title_match_mode,
        tag=parsed_tag,
        tag_match_mode=tag_match_mode,
        context_length=context_length,
        include_content=include_content,
        modified_since=modified_since,
        modified_until=modified_until,
        created_since=created_since,
        created_until=created_until,
        page_size=page_size,
        page=page,
        max_matches_per_file=max_matches_per_file
    )

@mcp.tool(
    annotations={
        "title": "Get Obsidian Note Content",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
async def get_note_content(path: str) -> Dict[str, Any]:
    """
    Get the full content and metadata of a specific note by path.
    
    Args:
        path: Full path to the note within the vault
    """
    try:
        note_data = await client.get_note_metadata(path)
        return {
            "success": True,
            "data": note_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get note at path '{path}': {str(e)}",
            "data": None
        }

@mcp.tool(
    annotations={
        "title": "Browse Obsidian Vault Structure",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
async def browse_vault_structure(path: str = "", include_files: bool = False, recursive: bool = False) -> Dict[str, Any]:
    """
    Browse vault directory structure.
    
    Args:
        path: Path to browse from (defaults to vault root)
        include_files: Include files in listing (default: False, folders only)
        recursive: List nested contents recursively
    """
    try:
        # Remove leading/trailing quotes and whitespace 
        clean_path = path.strip().strip('"\'')
        items = await client.browse_vault(clean_path, include_files, recursive)
        
        directories = [item for item in items if item.endswith('/')]
        files = [item for item in items if not item.endswith('/')]
        
        return {
            "success": True,
            "path": clean_path,
            "include_files": include_files,
            "recursive": recursive,
            "directories": directories,
            "files": files if include_files else [],
            "total_directories": len(directories),
            "total_files": len(files) if include_files else 0,
            "total_items": len(items)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to browse vault structure for path '{path}': {str(e)}",
            "path": path,
            "include_files": include_files,
            "recursive": recursive,
            "directories": [],
            "files": [],
            "total_directories": 0,
            "total_files": 0,
            "total_items": 0
        }

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()