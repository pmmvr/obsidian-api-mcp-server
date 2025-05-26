from unittest.mock import patch
from behave import given, when, then
import json


@given('the Obsidian API is available')
def step_obsidian_api_available(context):
    context.base_url = "https://localhost:27124"
    context.api_key = "test-api-key"


@given('the vault contains notes with content "{content}"')
def step_vault_contains_content(context, content):
    context.mock_search_results = [
        {
            "filename": "test-note.md",
            "score": 100,
            "matches": [
                {
                    "context": f"Some text with {content} in the middle",
                    "match": {"start": 15, "end": 15 + len(content)}
                }
            ]
        }
    ]


@given('the vault has a directory structure with files and folders')
def step_vault_has_structure(context):
    context.mock_api_files = ["daily/", "projects/", "README.md", "index.md"]


@given('the vault contains notes created on different dates')
def step_vault_notes_different_create_dates(context):
    context.mock_files_list = ["old-note.md", "new-note.md"]
    context.mock_metadata_responses = {
        "old-note.md": {"stat": {"mtime": 1703462400000, "ctime": 1703462400000}},  # Dec 2023
        "new-note.md": {"stat": {"mtime": 1704672000000, "ctime": 1704672000000}}   # Jan 2024
    }


@given('the vault contains notes with titles "{title1}", "{title2}", and "{title3}"')
def step_vault_notes_with_titles(context, title1, title2, title3):
    context.mock_files_list = [f"{title1}.md", f"{title2}.md", f"{title3}.md"]
    context.mock_metadata_base = {"stat": {"mtime": 1704067200000, "ctime": 1704067200000}}


@given('the vault contains notes in projects and daily directories')
def step_vault_notes_in_directories(context):
    context.mock_files_list = ["projects/work.md", "projects/personal.md", "daily/2024-01-01.md", "other/random.md"]
    context.mock_metadata_base = {"stat": {"mtime": 1704067200000, "ctime": 1704067200000}}


@given('the vault contains notes with "{content1}" and "{content2}"')
def step_vault_notes_with_content(context, content1, content2):
    context.mock_files_list = ["note1.md", "note2.md"]
    context.mock_note_contents = {
        "note1.md": {"content": f"Some {content1} here", "stat": {"mtime": 1704067200000, "ctime": 1704067200000}},
        "note2.md": {"content": f"Another {content2} there", "stat": {"mtime": 1704067200000, "ctime": 1704067200000}}
    }


@given('the vault contains notes with tags "{tag1}" and "{tag2}"')
def step_vault_notes_with_tags(context, tag1, tag2):
    context.mock_files_list = ["project-note.md", "meeting-note.md", "other-note.md"]
    context.mock_tag_contents = {
        "project-note.md": {
            "content": f"This is a project note #{tag1}",
            "frontmatter": {"tags": [tag1]},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        },
        "meeting-note.md": {
            "content": f"This is a meeting note #{tag2}",
            "frontmatter": {"tags": [tag2]},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        },
        "other-note.md": {
            "content": "This note has no tags",
            "frontmatter": {},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        }
    }


@given('the vault contains notes with multiple tags')
def step_vault_notes_with_multiple_tags(context):
    context.mock_files_list = ["urgent-project.md", "project-only.md", "urgent-only.md", "no-tags.md"]
    context.mock_multi_tag_contents = {
        "urgent-project.md": {
            "content": "This is urgent project work #project #urgent",
            "frontmatter": {"tags": ["project", "urgent"]},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        },
        "project-only.md": {
            "content": "This is project work #project",
            "frontmatter": {"tags": ["project"]},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        },
        "urgent-only.md": {
            "content": "This is urgent #urgent",
            "frontmatter": {"tags": ["urgent"]},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        },
        "no-tags.md": {
            "content": "This note has no tags",
            "frontmatter": {},
            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
        }
    }


@when('I call the search_vault tool with query "{query}"')
def step_call_search_tool(context, query):
    from obsidian_mcp.server import search_vault
    
    async def run_tool():
        # Mock only the external HTTP calls to Obsidian API
        with patch('httpx.AsyncClient.request') as mock_request:
            # Set up mock responses for different API endpoints
            def mock_api_response(method, url, **kwargs):
                if '/search/simple/' in url:
                    # Mock search endpoint
                    response = type('MockResponse', (), {
                        'status_code': 200,
                        'json': lambda *args, **kwargs: context.mock_search_results,
                        'raise_for_status': lambda *args, **kwargs: None
                    })()
                    return response
                elif '/vault/' in url and not url.endswith('/'):
                    # Mock note metadata endpoint
                    response = type('MockResponse', (), {
                        'status_code': 200,
                        'json': lambda *args, **kwargs: {
                            "stat": {"mtime": 1704067200000, "ctime": 1704067200000}
                        },
                        'raise_for_status': lambda *args, **kwargs: None
                    })()
                    return response
                else:
                    # Default response
                    response = type('MockResponse', (), {
                        'status_code': 404,
                        'raise_for_status': lambda *args, **kwargs: None
                    })()
                    return response
            
            mock_request.side_effect = mock_api_response
            
            # Call the actual MCP tool function - this is blackbox interface
            return await search_vault(query=query)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call the browse_vault_structure tool with include_files True')
def step_call_browse_tool_with_files(context):
    from obsidian_mcp.server import browse_vault_structure
    
    async def run_tool():
        # Mock only external HTTP calls to API
        with patch('httpx.AsyncClient.request') as mock_request:
            # Mock vault listing endpoint to return files and folders
            response = type('MockResponse', (), {
                'status_code': 200,
                'json': lambda *args, **kwargs: {"files": context.mock_api_files},
                'raise_for_status': lambda *args, **kwargs: None
            })()
            mock_request.return_value = response
            
            # Call actual MCP tool function with include_files=True
            return await browse_vault_structure(include_files=True)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call the get_note_content tool with path "{path}"')
def step_call_get_note_tool(context, path):
    from obsidian_mcp.server import get_note_content
    
    async def run_tool():
        # Mock only external HTTP calls to API
        with patch('httpx.AsyncClient.request') as mock_request:
            if path == "missing-note.md":
                # Mock 404 for missing note
                def raise_error(*args, **kwargs):
                    raise Exception("Note not found")
                
                response = type('MockResponse', (), {
                    'status_code': 404,
                    'raise_for_status': raise_error
                })()
                mock_request.return_value = response
            else:
                # Mock successful retrieval
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {
                        "content": "Daily note content for January 15th",
                        "stat": {"mtime": 1704067200000, "ctime": 1704067200000},
                        "frontmatter": {}
                    },
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                mock_request.return_value = response
            
            # Call actual tool function
            return await get_note_content(path)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@then('the tool should return successful results')
def step_verify_successful_results(context):
    assert context.tool_result.get("success") is True
    assert "results" in context.tool_result or "data" in context.tool_result


@then('the results should contain the searched content')
def step_verify_search_content(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) > 0
    # Verify actual search result structure
    result = context.tool_result["results"][0]
    assert "matches" in result
    assert len(result["matches"]) > 0


@then('the tool should return both files and folders')
def step_verify_files_and_folders_returned(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["directories"]) > 0  # Should have dir
    assert len(context.tool_result["files"]) > 0  # Should have files when include_files=True
    assert context.tool_result["include_files"] is True


@then('the tool should return an error')
def step_verify_error_result(context):
    assert context.tool_result.get("success") is False
    assert "error" in context.tool_result


@when('I call search_vault tool with created_since "{date}"')
def step_call_search_with_created_since(context, date):
    from obsidian_mcp.server import search_vault
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    # Extract filename from URL to return correct metadata
                    filename = url.split('/')[-1]
                    if filename in context.mock_metadata_responses:
                        response = type('MockResponse', (), {
                            'status_code': 200,
                            'json': lambda *args, **kwargs: context.mock_metadata_responses[filename],
                            'raise_for_status': lambda *args, **kwargs: None
                        })()
                        return response
                    
                # Default: return file list for filter-only search
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(created_since=date)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call search_vault tool with title_contains {title_list} and match mode "{mode}"')
def step_call_search_with_title_contains(context, title_list, mode):
    from obsidian_mcp.server import search_vault
    import json
    
    # Parse the title list from string representation
    title_contains = json.loads(title_list)
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    response = type('MockResponse', (), {
                        'status_code': 200,
                        'json': lambda *args, **kwargs: context.mock_metadata_base,
                        'raise_for_status': lambda *args, **kwargs: None
                    })()
                    return response
                    
                # Return file list for filter-only search  
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(title_contains=title_contains, title_match_mode=mode)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call search_vault tool with search_in_path "{path}"')
def step_call_search_with_path(context, path):
    from obsidian_mcp.server import search_vault
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    response = type('MockResponse', (), {
                        'status_code': 200,
                        'json': lambda *args, **kwargs: context.mock_metadata_base,
                        'raise_for_status': lambda *args, **kwargs: None
                    })()
                    return response
                    
                # Return file list for filter-only search
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(search_in_path=path)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call search_vault tool with regex "{pattern}"')
def step_call_search_with_regex(context, pattern):
    from obsidian_mcp.server import search_vault
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    # Extract filename from URL to return appropiiate content
                    filename = url.split('/')[-1]
                    if filename in context.mock_note_contents:
                        response = type('MockResponse', (), {
                            'status_code': 200,
                            'json': lambda *args, **kwargs: context.mock_note_contents[filename],
                            'raise_for_status': lambda *args, **kwargs: None
                        })()
                        return response
                    
                # Return file list for Regex search
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(query=pattern, query_type="regex")
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call search_vault tool with tag "{tag}"')
def step_call_search_with_tag(context, tag):
    from obsidian_mcp.server import search_vault
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    # Extract filename from URL to return appropriate content
                    filename = url.split('/')[-1]
                    if filename in context.mock_tag_contents:
                        response = type('MockResponse', (), {
                            'status_code': 200,
                            'json': lambda *args, **kwargs: context.mock_tag_contents[filename],
                            'raise_for_status': lambda *args, **kwargs: None
                        })()
                        return response
                    
                # Return file list for tag search
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(tag=tag)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@when('I call search_vault tool with tags {tag_list} and match mode "{mode}"')
def step_call_search_with_multiple_tags(context, tag_list, mode):
    from obsidian_mcp.server import search_vault
    import json
    
    # Parse the tag list from string representation
    tags = json.loads(tag_list)
    
    async def run_tool():
        with patch('httpx.AsyncClient.request') as mock_request:
            def mock_api_response(method, url, **kwargs):
                if '/vault/' in url and not url.endswith('/'):
                    # Extract filename from URL to return appropriate content
                    filename = url.split('/')[-1]
                    if filename in context.mock_multi_tag_contents:
                        response = type('MockResponse', (), {
                            'status_code': 200,
                            'json': lambda *args, **kwargs: context.mock_multi_tag_contents[filename],
                            'raise_for_status': lambda *args, **kwargs: None
                        })()
                        return response
                    
                # Return file list for tag search
                response = type('MockResponse', (), {
                    'status_code': 200,
                    'json': lambda *args, **kwargs: {"files": context.mock_files_list},
                    'raise_for_status': lambda *args, **kwargs: None
                })()
                return response
            
            mock_request.side_effect = mock_api_response
            return await search_vault(tag=tags, tag_match_mode=mode)
    
    context.tool_result = context.loop.run_until_complete(run_tool())


@then('the tool should return only notes created after that date')
def step_verify_created_since_filter(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 1  # Only new-note.md should match
    assert context.tool_result["results"][0]["path"] == "new-note.md"


@then('the tool should return notes matching either foo or bar')
def step_verify_title_or_match(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 2  # foo project.md and bar chart.md
    paths = [result["path"] for result in context.tool_result["results"]]
    assert "foo project.md" in paths
    assert "bar chart.md" in paths
    assert "baz notes.md" not in paths


@then('the tool should return only notes containing both foo and bar')
def step_verify_title_and_match(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 1  # Only "foo AND bar project.md"
    assert context.tool_result["results"][0]["path"] == "foo and bar project.md"


@then('the tool should return only notes from projects directory')
def step_verify_path_filter(context):
    assert context.tool_result["success"] is True
    for result in context.tool_result["results"]:
        assert result["path"].startswith("projects/")


@then('the tool should return notes matching the regex pattern')
def step_verify_regex_match(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) > 0  # Should find notes with foo OR bar content


@then('the tool should return only notes tagged with project')
def step_verify_tag_filter(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 1  # Only project-note.md should match
    assert context.tool_result["results"][0]["path"] == "project-note.md"


@then('the tool should return notes with either project or urgent tags')
def step_verify_multiple_tags_or_filter(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 3  # urgent-project.md, project-only.md, urgent-only.md
    paths = [result["path"] for result in context.tool_result["results"]]
    assert "urgent-project.md" in paths
    assert "project-only.md" in paths
    assert "urgent-only.md" in paths
    assert "no-tags.md" not in paths


@then('the tool should return only notes with both project and urgent tags')
def step_verify_multiple_tags_and_filter(context):
    assert context.tool_result["success"] is True
    assert len(context.tool_result["results"]) == 1  # Only urgent-project.md should match
    assert context.tool_result["results"][0]["path"] == "urgent-project.md"