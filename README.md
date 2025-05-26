# Obsidian MCP Server

An MCP (Model Context Protocol) server that enables AI agents to perform sophisticated knowledge discovery and analysis across your Obsidian vault through the Local REST API plugin.

## Why This Matters

This server transforms your Obsidian vault into a powerful knowledge base for AI agents, enabling complex multi-step workflows like:

- **"Retrieve notes from my 'Projects/Planning' folder containing 'roadmap' or 'timeline' in titles, created after April 1st, then analyze them for any blockers or dependencies and present a consolidated risk assessment with references to the source notes"**

- **"Find all notes tagged with 'research' or 'analysis' from the last month, scan their content for incomplete sections or open questions, then cross-reference with my 'Team/Expertise' notes to suggest which colleagues could help address each gap"**

- **"Get the complete content of meeting notes from 'Leadership/Quarterly' containing 'budget' or 'headcount', analyze them for action items assigned to my department, and create a chronological timeline with source note references"**

The server's advanced filtering, regex support, and full content retrieval capabilities allow agents to perform nuanced knowledge work that would take hours manually.

## Prerequisites

1. Install the [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin in your Obsidian vault
2. Configure and enable the plugin in Obsidian settings
3. Note the API URL (default: `https://localhost:27124`) and API key if you've set one

## Installation

### From PyPI (Recommended)

```bash
# Install from PyPI
pip install obsidian-api-mcp-server

# Or with uv
uv pip install obsidian-api-mcp-server
```

### Add to MCP Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "obsidian-api-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "obsidian-api-mcp-server>=1.0.1",
        "obsidian-api-mcp"
      ],
      "env": {
        "OBSIDIAN_API_URL": "https://localhost:27124",
        "OBSIDIAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/pmmvr/obsidian-api-mcp-server
cd obsidian-api-mcp-server

# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Configuration

Set environment variables for the Obsidian API:

```bash
# Required: Obsidian API URL (HTTPS by default)
export OBSIDIAN_API_URL="https://localhost:27124"  # Default

# Optional: API key if you've configured authentication
export OBSIDIAN_API_KEY="your-api-key-here"
```

**Important Security Note**: Avoid hardcoding your `OBSIDIAN_API_KEY` directly into scripts or committing it to version control. Consider using a `.env` file (which is included in the `.gitignore` of this project) and a library like `python-dotenv` to manage your API key, or use environment variables managed by your operating system or shell.

**Note**: The server defaults to HTTPS and disables SSL certificate verification for self-signed certificates commonly used with local Obsidian instances. For HTTP connections, set `OBSIDIAN_API_URL="http://localhost:27123"`.

## Usage

Run the MCP server:

```bash
obsidian-mcp
```

## Available Tools

The server provides three powerful tools:

1. **`search_vault`** - Advanced search with flexible filters and full content retrieval:
   - `query` - Text or regex search across note content (optional)
   - `query_type` - Search type: "text" (default) or "regex"
   - `search_in_path` - Limit search to specific folder path
   - `title_contains` - Filter by text in note titles (string, array, or JSON string)
   - `title_match_mode` - How to match multiple terms: "any" (OR) or "all" (AND)
   - `tag` - Filter by tag (string, array, or JSON string - searches frontmatter and inline #tags)
   - `tag_match_mode` - How to match multiple tags: "any" (OR) or "all" (AND)
   - `context_length` - Amount of content to return (set high for full content)
   - `include_content` - Boolean to retrieve complete content of all matching notes
   - `created_since/until` - Filter by creation date
   - `modified_since/until` - Filter by modification date
   - `page_size` - Results per page
   - `max_matches_per_file` - Limit matches per note
   
   **Key Features**: 
   - When no `query` is provided, automatically returns full content for filter-only searches
   - `include_content=True` forces full content retrieval for any search
   - Supports regex patterns for complex text matching (OR conditions, case-insensitive search, etc.)

2. **`get_note_content`** - Retrieve complete content and metadata of a specific note by path

3. **`browse_vault_structure`** - Navigate vault directory structure efficiently:
   - `path` - Directory to browse (defaults to vault root)  
   - `include_files` - Boolean to include files (default: False, folders only for speed)
   - `recursive` - Boolean to browse all nested directories

## Example Use Cases

### Basic Searches
1. **Find notes by title in a specific folder:**
   ```
   search_vault(
     search_in_path="Work/Projects/",
     title_contains="meeting"
   )
   ```

2. **Find notes with multiple title terms (OR logic):**
   ```
   search_vault(
     title_contains=["foo", "bar", "fizz", "buzz"],
     title_match_mode="any"  # Default
   )
   ```

3. **Find notes with ALL title terms (AND logic):**
   ```
   search_vault(
     title_contains=["project", "2024"],
     title_match_mode="all"
   )
   ```

4. **Get all recent notes with full content:**
   ```
   search_vault(
     modified_since="2025-05-20",
     include_content=True
   )
   ```

5. **Text search with context:**
   ```
   search_vault(
     query="API documentation",
     search_in_path="Engineering/",
     context_length=500
   )
   ```

6. **Search by tag:**
   ```
   search_vault(
     tag="project"
   )
   ```

7. **Regex search for OR conditions:**
   ```
   search_vault(
     query="foo|bar",
     query_type="regex",
     search_in_path="Projects/"
   )
   ```

8. **Regex search for tasks assigned to specific people:**
   ```
   search_vault(
     query="(TODO|FIXME|ACTION).*@(alice|bob)",
     query_type="regex",
     search_in_path="Work/Meetings/"
   )
   ```

### Advanced Multi-Step Workflows

These examples demonstrate how agents can chain together sophisticated knowledge discovery tasks:

9. **Strategic Project Analysis:**
   ```
   # Step 1: Get all project documentation
   search_vault(
     search_in_path="Projects/Infrastructure/",
     title_contains=["planning", "requirements", "architecture"],
     title_match_mode="any",
     include_content=True
   )
   
   # Step 2: Find related technical discussions
   search_vault(
     tag=["infrastructure", "technical-debt"],
     tag_match_mode="any",
     modified_since="2025-04-01",
     include_content=True
   )
   ```
   *Agent can then analyze dependencies, identify risks, and recommend resource allocation*

10. **Meeting Action Item Mining:**
   ```
   # Get all recent meeting notes with full content
   search_vault(
     search_in_path="Meetings/",
     title_contains=["standup", "planning", "retrospective"],
     title_match_mode="any",
     created_since="2025-05-01",
     include_content=True
   )
   ```
   *Agent scans content for action items, extracts assignments, and creates chronological tracking*

11. **Research Gap Analysis:**
   ```
   # Find research notes with questions or gaps
   search_vault(
     query="(TODO|QUESTION|INVESTIGATE|UNCLEAR)",
     query_type="regex",
     tag=["research", "analysis"],
     tag_match_mode="any",
     include_content=True
   )
   
   # Cross-reference with team expertise
   search_vault(
     search_in_path="Team/",
     tag=["expertise", "skills"],
     tag_match_mode="any",
     include_content=True
   )
   ```
   *Agent identifies knowledge gaps and suggests team members who could help*

12. **Vault Structure Exploration:**
   ```
   # Quick organizational overview
   browse_vault_structure(recursive=True)
   
   # Deep dive into specific areas
   browse_vault_structure(
     path="Projects/CurrentSprint/",
     include_files=True,
     recursive=True
   )
   ```

13. **Tag-Based Knowledge Mapping:**
   ```
   # Find notes with multiple tags (AND logic)
   search_vault(
     tag=["project", "urgent"],
     tag_match_mode="all",
     include_content=True
   )
   
   # Find notes with any relevant tags (OR logic)
   search_vault(
     tag=["architecture", "design", "implementation"],
     tag_match_mode="any",
     modified_since="2025-04-15"
   )
   ```

## Development

```bash
# Install with test dependencies
uv pip install -e ".[test]"

# Run the server
python -m obsidian_mcp.server

# Run tests
uv run behave features/blackbox_tests.feature
# Or use the test runner
python run_tests.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.