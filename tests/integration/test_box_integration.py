"""
Integration tests for Box API via mcp-openapi-proxy, FastMCP mode.
Requires BOX_API_KEY in .env to run.
"""

import os
import json
import pytest
from dotenv import load_dotenv
from mcp_openapi_proxy.utils import fetch_openapi_spec
from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

# Load .env file from project root if it exists
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

# --- Configuration ---
BOX_API_KEY = os.getenv("BOX_API_KEY")
# Use the spec from APIs.guru directory
SPEC_URL = "https://raw.githubusercontent.com/APIs-guru/openapi-directory/main/APIs/box.com/2.0.0/openapi.yaml"
# Whitelist the endpoints needed for these tests
TOOL_WHITELIST = "/folders/{folder_id},/recent_items,/folders/{folder_id}/items" # Added /folders/{folder_id}/items
TOOL_PREFIX = "box_"
# Box API uses Bearer token auth
API_AUTH_TYPE = "Bearer"
# Box API base URL (though the spec should define this)
SERVER_URL_OVERRIDE = "https://api.box.com/2.0"

# --- Helper Function ---
def get_tool_name(tools, original_name):
    """Find tool name by original endpoint name (e.g., 'GET /path')."""
    # Ensure tools is a list of dictionaries
    if not isinstance(tools, list) or not all(isinstance(t, dict) for t in tools):
        print(f"DEBUG: Invalid tools structure: {tools}")
        return None
    # Find the tool matching the original name (method + path)
    tool = next((t for t in tools if t.get("original_name") == original_name), None)
    if not tool:
        print(f"DEBUG: Tool not found for {original_name}. Available tools: {[t.get('original_name', 'N/A') for t in tools]}")
    return tool.get("name") if tool else None

# --- Pytest Fixture ---
@pytest.fixture
def box_setup(reset_env_and_module):
    """Fixture to set up Box env and list functions."""
    env_key = reset_env_and_module
    # Corrected line 46: Concatenate "..." within the expression
    print(f"DEBUG: BOX_API_KEY: {(BOX_API_KEY[:5] + '...') if BOX_API_KEY else 'Not set'}")
    if not BOX_API_KEY or "your_key" in BOX_API_KEY.lower():
        print("DEBUG: Skipping due to missing or placeholder BOX_API_KEY")
        pytest.skip("BOX_API_KEY missing or placeholder—please set it in .env!")

    # Set environment variables for the proxy
    os.environ[env_key] = SPEC_URL
    os.environ["API_KEY"] = BOX_API_KEY
    os.environ["API_AUTH_TYPE"] = API_AUTH_TYPE
    os.environ["TOOL_WHITELIST"] = TOOL_WHITELIST
    os.environ["TOOL_NAME_PREFIX"] = TOOL_PREFIX
    os.environ["SERVER_URL_OVERRIDE"] = SERVER_URL_OVERRIDE # Ensure proxy uses correct base URL
    os.environ["DEBUG"] = "true"
    print(f"DEBUG: API_KEY set for proxy: {os.environ['API_KEY'][:5]}...")

    print(f"DEBUG: Fetching spec from {SPEC_URL}")
    spec = fetch_openapi_spec(SPEC_URL)
    assert spec, f"Failed to fetch spec from {SPEC_URL}"

    print("DEBUG: Listing available functions via proxy")
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    print(f"DEBUG: Tools listed by proxy: {tools_json}")
    assert tools, "No functions generated by proxy"
    assert isinstance(tools, list), "Generated functions should be a list"

    return env_key, tools

# --- Test Functions ---
@pytest.mark.integration
def test_box_get_folder_info(box_setup):
    """Test getting folder info via the proxy."""
    env_key, tools = box_setup
    folder_id = "0"  # Root folder ID
    original_name = "GET /folders/{folder_id}" # Use the actual path template

    # Find the normalized tool name
    tool_name = get_tool_name(tools, original_name)
    assert tool_name, f"Tool for {original_name} not found!"
    print(f"DEBUG: Found tool name: {tool_name}")

    print(f"DEBUG: Calling proxy function {tool_name} for folder_id={folder_id}")
    response_json_str = call_function(
        function_name=tool_name,
        parameters={"folder_id": folder_id},
        env_key=env_key
    )
    print(f"DEBUG: Raw response string from proxy: {response_json_str}")
    # --- Add size debugging ---
    response_size_bytes = len(response_json_str.encode('utf-8'))
    print(f"DEBUG: Raw response size from proxy (get_folder_info): {response_size_bytes} bytes ({len(response_json_str)} chars)")
    # --- End size debugging ---

    try:
        # The proxy returns the API response as a JSON string, parse it
        response_data = json.loads(response_json_str)

        # Check for API errors returned via the proxy
        if isinstance(response_data, dict) and "error" in response_data:
            print(f"DEBUG: Error received from proxy/API: {response_data['error']}")
            if "401" in response_data["error"] or "invalid_token" in response_data["error"]:
                assert False, "BOX_API_KEY is invalid—please check your token!"
            assert False, f"Box API returned an error via proxy: {response_json_str}"

        # Assertions on the actual Box API response data
        assert isinstance(response_data, dict), f"Parsed response is not a dictionary: {response_data}"
        assert "id" in response_data and response_data["id"] == folder_id, f"Folder ID mismatch or missing: {response_data}"
        assert "name" in response_data, f"Folder name missing: {response_data}"
        assert response_data.get("type") == "folder", f"Incorrect type: {response_data}"
        print(f"DEBUG: Successfully got info for folder: {response_data.get('name')}")

    except json.JSONDecodeError:
        assert False, f"Response from proxy is not valid JSON: {response_json_str}"

@pytest.mark.integration
def test_box_list_folder_contents(box_setup):
    """Test listing folder contents via the proxy (using the same GET /folders/{id} endpoint)."""
    env_key, tools = box_setup
    folder_id = "0"  # Root folder ID
    original_name = "GET /folders/{folder_id}" # Use the actual path template

    # Find the normalized tool name (same as the previous test)
    tool_name = get_tool_name(tools, original_name)
    assert tool_name, f"Tool for {original_name} not found!"
    print(f"DEBUG: Found tool name: {tool_name}")

    print(f"DEBUG: Calling proxy function {tool_name} for folder_id={folder_id}")
    response_json_str = call_function(
        function_name=tool_name,
        parameters={"folder_id": folder_id},
        env_key=env_key
    )
    print(f"DEBUG: Raw response string from proxy: {response_json_str}")
    # --- Add size debugging ---
    response_size_bytes = len(response_json_str.encode('utf-8'))
    print(f"DEBUG: Raw response size from proxy (list_folder_contents): {response_size_bytes} bytes ({len(response_json_str)} chars)")
    # --- End size debugging ---

    try:
        # Parse the JSON string response from the proxy
        response_data = json.loads(response_json_str)

        # Check for API errors
        if isinstance(response_data, dict) and "error" in response_data:
            print(f"DEBUG: Error received from proxy/API: {response_data['error']}")
            if "401" in response_data["error"] or "invalid_token" in response_data["error"]:
                assert False, "BOX_API_KEY is invalid—please check your token!"
            assert False, f"Box API returned an error via proxy: {response_json_str}"

        # Assertions on the Box API response structure for folder contents
        assert isinstance(response_data, dict), f"Parsed response is not a dictionary: {response_data}"
        assert "item_collection" in response_data, f"Key 'item_collection' missing in response: {response_data}"
        entries = response_data["item_collection"].get("entries")
        assert isinstance(entries, list), f"'entries' is not a list or missing: {response_data.get('item_collection')}"

        # Print the contents for verification during test run
        print("\nBox root folder contents (via proxy):")
        for entry in entries:
            print(f"  {entry.get('type', 'N/A')}: {entry.get('name', 'N/A')} (id: {entry.get('id', 'N/A')})")

        # Optionally check structure of at least one entry if list is not empty
        if entries:
            entry = entries[0]
            assert "type" in entry
            assert "id" in entry
            assert "name" in entry
        print(f"DEBUG: Successfully listed {len(entries)} items in root folder.")

    except json.JSONDecodeError:
        assert False, f"Response from proxy is not valid JSON: {response_json_str}"

@pytest.mark.integration
def test_box_get_recent_items(box_setup):
    """Test getting recent items via the proxy."""
    env_key, tools = box_setup
    original_name = "GET /recent_items"

    # Find the normalized tool name
    tool_name = get_tool_name(tools, original_name)
    assert tool_name, f"Tool for {original_name} not found!"
    print(f"DEBUG: Found tool name: {tool_name}")

    print(f"DEBUG: Calling proxy function {tool_name} for recent items")
    # No parameters needed for the basic call
    response_json_str = call_function(
        function_name=tool_name,
        parameters={},
        env_key=env_key
    )
    print(f"DEBUG: Raw response string from proxy: {response_json_str}")
    # --- Add size debugging ---
    response_size_bytes = len(response_json_str.encode('utf-8'))
    print(f"DEBUG: Raw response size from proxy (get_recent_items): {response_size_bytes} bytes ({len(response_json_str)} chars)")
    # --- End size debugging ---

    try:
        # Parse the JSON string response from the proxy
        response_data = json.loads(response_json_str)

        # Check for API errors
        if isinstance(response_data, dict) and "error" in response_data:
            print(f"DEBUG: Error received from proxy/API: {response_data['error']}")
            if "401" in response_data["error"] or "invalid_token" in response_data["error"]:
                assert False, "BOX_API_KEY is invalid—please check your token!"
            assert False, f"Box API returned an error via proxy: {response_json_str}"

        # Assertions on the Box API response structure for recent items
        assert isinstance(response_data, dict), f"Parsed response is not a dictionary: {response_data}"
        assert "entries" in response_data, f"Key 'entries' missing in response: {response_data}"
        entries = response_data["entries"]
        assert isinstance(entries, list), f"'entries' is not a list: {entries}"

        # Print the recent items for verification
        print("\nBox recent items (via proxy):")
        for entry in entries[:5]: # Print first 5 for brevity
             item = entry.get("item", {})
             print(f"  {entry.get('type', 'N/A')} - {item.get('type', 'N/A')}: {item.get('name', 'N/A')} (id: {item.get('id', 'N/A')})")

        # Optionally check structure of at least one entry if list is not empty
        if entries:
            entry = entries[0]
            assert "type" in entry
            assert "item" in entry and isinstance(entry["item"], dict)
            assert "id" in entry["item"]
            assert "name" in entry["item"]
        print(f"DEBUG: Successfully listed {len(entries)} recent items.")

    except json.JSONDecodeError:
        assert False, f"Response from proxy is not valid JSON: {response_json_str}"

@pytest.mark.integration
def test_box_list_folder_items_endpoint(box_setup):
    """Test listing folder items via the dedicated /folders/{id}/items endpoint."""
    env_key, tools = box_setup
    folder_id = "0"  # Root folder ID
    original_name = "GET /folders/{folder_id}/items" # The specific items endpoint

    # Find the normalized tool name
    tool_name = get_tool_name(tools, original_name)
    assert tool_name, f"Tool for {original_name} not found!"
    print(f"DEBUG: Found tool name: {tool_name}")

    print(f"DEBUG: Calling proxy function {tool_name} for folder_id={folder_id}")
    response_json_str = call_function(
        function_name=tool_name,
        parameters={"folder_id": folder_id}, # Pass folder_id parameter
        env_key=env_key
    )
    print(f"DEBUG: Raw response string from proxy: {response_json_str}")
    # --- Add size debugging ---
    response_size_bytes = len(response_json_str.encode('utf-8'))
    print(f"DEBUG: Raw response size from proxy (list_folder_items_endpoint): {response_size_bytes} bytes ({len(response_json_str)} chars)")
    # --- End size debugging ---

    try:
        # Parse the JSON string response from the proxy
        response_data = json.loads(response_json_str)

        # Check for API errors
        if isinstance(response_data, dict) and "error" in response_data:
            print(f"DEBUG: Error received from proxy/API: {response_data['error']}")
            if "401" in response_data["error"] or "invalid_token" in response_data["error"]:
                assert False, "BOX_API_KEY is invalid—please check your token!"
            assert False, f"Box API returned an error via proxy: {response_json_str}"

        # Assertions on the Box API response structure for listing items
        assert isinstance(response_data, dict), f"Parsed response is not a dictionary: {response_data}"
        assert "entries" in response_data, f"Key 'entries' missing in response: {response_data}"
        entries = response_data["entries"]
        assert isinstance(entries, list), f"'entries' is not a list: {entries}"
        assert "total_count" in response_data, f"Key 'total_count' missing: {response_data}"

        # Print the items for verification
        print(f"\nBox folder items (via {original_name} endpoint):")
        for entry in entries:
            print(f"  {entry.get('type', 'N/A')}: {entry.get('name', 'N/A')} (id: {entry.get('id', 'N/A')})")

        # Optionally check structure of at least one entry if list is not empty
        if entries:
            entry = entries[0]
            assert "type" in entry
            assert "id" in entry
            assert "name" in entry
        print(f"DEBUG: Successfully listed {len(entries)} items (total_count: {response_data['total_count']}) using {original_name}.")

    except json.JSONDecodeError:
        assert False, f"Response from proxy is not valid JSON: {response_json_str}"

