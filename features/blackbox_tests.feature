Feature: MCP Server Blackbox Tests
  Test the MCP server tools as a blackbox, mocking only external dependencies

  Scenario: Search vault tool returns results
    Given the Obsidian API is available
    And the vault contains notes with content "project meeting"
    When I call the search_vault tool with query "project meeting"
    Then the tool should return successful results
    And the results should contain the searched content

  Scenario: Browse vault tool respects include_files parameter
    Given the Obsidian API is available
    And the vault has a directory structure with files and folders
    When I call the browse_vault_structure tool with include_files True
    Then the tool should return both files and folders

  Scenario: Get note content tool handles missing notes
    Given the Obsidian API is available
    When I call the get_note_content tool with path "missing-note.md"
    Then the tool should return an error

  Scenario: Get note content tool retrieves existing notes
    Given the Obsidian API is available
    When I call the get_note_content tool with path "daily/2024-01-15.md"
    Then the tool should return successful results

  Scenario: Search vault with created since date filter
    Given the Obsidian API is available
    And the vault contains notes created on different dates
    When I call search_vault tool with created_since "2024-01-01"
    Then the tool should return only notes created after that date

  Scenario: Search vault with title contains OR matching
    Given the Obsidian API is available
    And the vault contains notes with titles "foo project", "bar chart", and "baz notes"
    When I call search_vault tool with title_contains ["foo", "bar"] and match mode "any"
    Then the tool should return notes matching either foo or bar

  Scenario: Search vault with title contains AND matching
    Given the Obsidian API is available
    And the vault contains notes with titles "foo and bar project", "foo notes", and "bar chart"
    When I call search_vault tool with title_contains ["foo", "bar"] and match mode "all"
    Then the tool should return only notes containing both foo and bar

  Scenario: Search vault within specific directory
    Given the Obsidian API is available
    And the vault contains notes in projects and daily directories
    When I call search_vault tool with search_in_path "projects/"
    Then the tool should return only notes from projects directory

  Scenario: Search vault with regex pattern
    Given the Obsidian API is available
    And the vault contains notes with "foo content" and "bar content"
    When I call search_vault tool with regex "(foo|bar)"
    Then the tool should return notes matching the regex pattern

  Scenario: Search vault by tag
    Given the Obsidian API is available
    And the vault contains notes with tags "project" and "meeting"
    When I call search_vault tool with tag "project"
    Then the tool should return only notes tagged with project

  Scenario: Search vault with multiple tags OR matching
    Given the Obsidian API is available
    And the vault contains notes with multiple tags
    When I call search_vault tool with tags ["project", "urgent"] and match mode "any"
    Then the tool should return notes with either project or urgent tags

  Scenario: Search vault with multiple tags AND matching
    Given the Obsidian API is available
    And the vault contains notes with multiple tags
    When I call search_vault tool with tags ["project", "urgent"] and match mode "all"
    Then the tool should return only notes with both project and urgent tags