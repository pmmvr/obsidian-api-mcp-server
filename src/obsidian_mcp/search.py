import os
import math
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obsidian_mcp.client import ObsidianClient
from obsidian_mcp.utils import format_timestamp, parse_date_filter


class SearchProcessor:
    """
    Processes search queries against an Obsidian vault, handling various filters,
    pagination, and result formatting.
    """
    def __init__(self, client: ObsidianClient):
        self.client = client
    
    async def _get_file_metadata(self, file_path: str, include_content_for_tags: bool = False) -> Optional[Dict[str, Any]]:
        try:
            note_metadata = await self.client.get_note_metadata(file_path)
            result = {
                "mtime": note_metadata["stat"]["mtime"],
                "ctime": note_metadata["stat"]["ctime"]
            }
            
            # Include content and tags if needed for tag filtering
            if include_content_for_tags:
                result["content"] = note_metadata.get("content", "")
                result["tags"] = note_metadata.get("frontmatter", {}).get("tags", [])
                
            return result
        except Exception:
            return None
    
    def _apply_filters(self, file_path: str, metadata: Dict[str, Any], 
                      search_path_prefix: str, title_contains: Optional[Union[str, List[str]]], title_match_mode: str,
                      tag: Optional[Union[str, List[str]]], tag_match_mode: str, since_date: Optional[datetime], until_date: Optional[datetime],
                      created_since_date: Optional[datetime], created_until_date: Optional[datetime]) -> bool:
        """
        Applies various filters to a file based on its path, metadata, and specified criteria.
        Returns True if the file passes all filters, False otherwise.
        """
        
        if search_path_prefix and not file_path.startswith(search_path_prefix):
            return False
        
        if title_contains:
            filename = os.path.basename(file_path).lower()
            if isinstance(title_contains, str):
                if title_contains.lower() not in filename:
                    return False
            else:
                terms = [term.lower() for term in title_contains]
                if title_match_mode == "all":
                    if not all(term in filename for term in terms):
                        return False
                else:
                    if not any(term in filename for term in terms):
                        return False
        
        # Check tag filter - tags are stored in frontmatter or content
        if tag:
            tags_found = metadata.get("tags", [])
            # Also check for inline tags in content if available
            content = metadata.get("content", "")
            if content:
                # Look for #tag format in content
                import re
                inline_tags = re.findall(r'#(\w+)', content)
                tags_found.extend(inline_tags)
            
            # Convert to lowercase for case-insensitive matching
            tags_found = [t.lower() for t in tags_found]
            
            # Handle multiple tags with AND/OR logic
            if isinstance(tag, str):
                # Single tag
                if tag.lower() not in tags_found:
                    return False
            else:
                # Multiple tags - apply OR/AND logic
                tags_to_match = [t.lower() for t in tag]
                if tag_match_mode == "all":
                    # ALL tags must be present (AND logic)
                    if not all(tag_term in tags_found for tag_term in tags_to_match):
                        return False
                else:  # tag_match_mode == "any" (default)
                    # ANY tag must be present (OR logic)
                    if not any(tag_term in tags_found for tag_term in tags_to_match):
                        return False
        
        file_mod_time = datetime.fromtimestamp(metadata["mtime"] / 1000)
        if since_date and file_mod_time < since_date:
            return False
        if until_date and file_mod_time > until_date:
            return False
        
        file_created_time = datetime.fromtimestamp(metadata["ctime"] / 1000)
        if created_since_date and file_created_time < created_since_date:
            return False
        if created_until_date and file_created_time > created_until_date:
            return False
        
        return True
    
    def _process_matches(self, api_result: Dict[str, Any], max_matches_per_file: int) -> List[Dict[str, Any]]:
        matches = []
        for match in api_result.get("matches", []):
            matches.append({
                "context": match.get("context", ""),
                "match_start": match.get("match", {}).get("start", 0),
                "match_end": match.get("match", {}).get("end", 0)
            })
        return matches[:max_matches_per_file]
    
    def _create_result_item(self, file_path: str, matches: List[Dict[str, Any]], 
                           metadata: Dict[str, Any], score: int) -> Dict[str, Any]:
        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "matches": matches,
            "modified_time": format_timestamp(metadata["mtime"]),
            "created_time": format_timestamp(metadata["ctime"]),
            "score": score
        }
    
    def _paginate_results(self, results: List[Dict[str, Any]], page: int, page_size: int) -> tuple:
        total_files_found = len(results)
        total_pages = math.ceil(total_files_found / page_size)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_results = results[start_index:end_index]
        
        also_found_in_files = None
        if total_pages > 1:
            # Collect filenames from other pages if pagination is active
            paginated_paths = {result["path"] for result in paginated_results}
            also_found_in_files = [
                result["filename"] for result in results
                if result["path"] not in paginated_paths
            ]
        
        return paginated_results, total_files_found, total_pages, also_found_in_files
    
    async def search(self, query: Optional[str] = None, query_type: str = "text", search_in_path: Optional[str] = None,
                    title_contains: Optional[Union[str, List[str]]] = None, title_match_mode: str = "any", 
                    tag: Optional[Union[str, List[str]]] = None, tag_match_mode: str = "any",
                    context_length: int = 100, include_content: bool = False,
                    modified_since: Optional[str] = None, modified_until: Optional[str] = None,
                    created_since: Optional[str] = None, created_until: Optional[str] = None,
                    page_size: int = 50, page: int = 1, max_matches_per_file: int = 5) -> Dict[str, Any]:
        
        date_filters = self._parse_date_filters(modified_since, modified_until, created_since, created_until)
        search_path_prefix = self._normalize_search_path(search_in_path)
        
        try:
            # Determine the base path for API search if a prefix is provided
            base_search_path = search_path_prefix.rstrip('/') if search_path_prefix else ""
            api_results = await self._get_api_results(query, query_type, context_length, base_search_path)
            filtered_results, total_matches_count = await self._process_results(
                api_results, search_path_prefix, title_contains, title_match_mode, tag, tag_match_mode, date_filters, max_matches_per_file, query, include_content
            )
            
            filtered_results.sort(key=lambda x: x["modified_time"], reverse=True)
            
            paginated_results, total_files_found, total_pages, also_found_in_files = self._paginate_results(
                filtered_results, page, page_size
            )
            
            message = self._create_response_message(
                total_matches_count, total_files_found, page, total_pages, 
                len(paginated_results), search_path_prefix
            )
            
            return {
                "success": True,
                "message": message,
                "results": paginated_results,
                "total_files_found": total_files_found,
                "total_matches_found": total_matches_count,
                "current_page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "also_found_in_files": also_found_in_files
            }
            
        except Exception as e:
            return self._create_error_response(str(e), page, page_size)
    
    def _parse_date_filters(self, modified_since: Optional[str], modified_until: Optional[str],
                           created_since: Optional[str], created_until: Optional[str]) -> Dict[str, Optional[datetime]]:
        return {
            "since_date": parse_date_filter(modified_since) if modified_since else None,
            "until_date": parse_date_filter(modified_until) if modified_until else None,
            "created_since_date": parse_date_filter(created_since) if created_since else None,
            "created_until_date": parse_date_filter(created_until) if created_until else None
        }
    
    def _normalize_search_path(self, search_in_path: Optional[str]) -> str:
        if not search_in_path:
            return ""
        search_path_prefix = search_in_path.strip("/")
        return search_path_prefix + "/" if search_path_prefix else ""
    
    async def _get_api_results(self, query: Optional[str], query_type: str, context_length: int, search_path: str = "") -> List[Dict[str, Any]]:
        if query and query.strip():
            if query_type == "regex":
                return await self._execute_regex_search(query, search_path)
            else:
                # Default to simple text search if query type is not regex or not specified
                return await self.client.search_simple(query, context_length)
        else:
            # If no query is provided, list all markdown files in the specified path
            all_files = await self.client.list_all_files(search_path, max_depth=8, max_files=1000)
            return [
                {
                    "filename": file_path,
                    "score": 0,
                    "matches": []
                }
                for file_path in all_files
                if file_path.endswith('.md')
            ]
    
    async def _execute_regex_search(self, regex_pattern: str, search_path: str = "") -> List[Dict[str, Any]]:
        import re
        
        try:
            if not regex_pattern.startswith('(?'):
                # Default to case-insensitive regex search if no flags are provided
                case_insensitive_pattern = f"(?i){regex_pattern}"
            else:
                case_insensitive_pattern = regex_pattern
            
            regex = re.compile(case_insensitive_pattern)
            all_files = await self.client.list_all_files(search_path, max_depth=8, max_files=1000)
            md_files = [f for f in all_files if f.endswith('.md')]
            
            formatted_results = []
            for file_path in md_files:
                try:
                    note_data = await self.client.get_note_metadata(file_path)
                    content = note_data.get("content", "")
                    
                    matches = list(regex.finditer(content))
                    if matches:
                        match_data = []
                        for match in matches[:5]: 
                            # Create a context window around each match
                            start = max(0, match.start() - 50)
                            end = min(len(content), match.end() + 50)
                            context = content[start:end]
                            match_data.append({
                                "context": context,
                                "match": {
                                    "start": match.start() - start,
                                    "end": match.end() - start
                                }
                            })
                        
                        formatted_results.append({
                            "filename": file_path,
                            "score": len(matches),
                            "matches": match_data
                        })
                except Exception:
                    continue
            
            return formatted_results
            
        except Exception as e:
            print(f"Regex search failed: {e}, falling back to simple search")
            return await self.client.search_simple(regex_pattern, 100)
    
    async def _process_results(self, api_results: List[Dict[str, Any]], search_path_prefix: str,
                              title_contains: Optional[Union[str, List[str]]], title_match_mode: str, tag: Optional[Union[str, List[str]]], tag_match_mode: str,
                              date_filters: Dict[str, Optional[datetime]], max_matches_per_file: int, query: Optional[str], include_content: bool = False) -> tuple:
        filtered_results = []
        total_matches_count = 0
        
        for api_result in api_results:
            file_path = api_result["filename"]
            # Include content if we need to filter by tags
            metadata = await self._get_file_metadata(file_path, include_content_for_tags=bool(tag))
            
            if not metadata:
                continue
            
            if not self._apply_filters(
                file_path, metadata, search_path_prefix, title_contains, title_match_mode, tag, tag_match_mode,
                date_filters["since_date"], date_filters["until_date"],
                date_filters["created_since_date"], date_filters["created_until_date"]
            ):
                continue
            
            all_matches = api_result.get("matches", [])
            matches = self._process_matches(api_result, max_matches_per_file)
            total_matches_count += len(all_matches)
            
            if include_content or (query is None or query.strip() == ""):
                # If include_content is true, or if there's no search query (listing all files),
                # attempt to fetch and include the full note content.
                try:
                    full_content = await self.client.get_note_metadata(file_path)
                    content_text = full_content.get("content", "")
                    if content_text:
                        matches = [{
                            "context": content_text,
                            "match_start": 0,
                            "match_end": len(content_text)
                        }]
                except Exception:
                    pass
            
            if matches or (query is None or query.strip() == ""):
                result_item = self._create_result_item(
                    file_path, matches, metadata, api_result.get("score", 0)
                )
                filtered_results.append(result_item)
        
        return filtered_results, total_matches_count
    
    def _create_response_message(self, total_matches_count: int, total_files_found: int,
                                page: int, total_pages: int, current_page_files: int,
                                search_path_prefix: str) -> str:
        message = (f"Found {total_matches_count} matches across {total_files_found} files. "
                  f"Showing page {page} of {total_pages} ({current_page_files} files on this page).")
        
        if search_path_prefix:
            message += f" Searched in path: {search_path_prefix}"
        
        return message
    
    def _create_error_response(self, error_msg: str, page: int, page_size: int) -> Dict[str, Any]:
        return {
            "success": False,
            "message": f"Search failed: {error_msg}",
            "results": [],
            "total_files_found": 0,
            "total_matches_found": 0,
            "current_page": page,
            "page_size": page_size,
            "total_pages": 0
        }