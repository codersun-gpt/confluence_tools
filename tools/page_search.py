from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from unit.confluence_session import ConfluenceSession


class PageSearchTool(Tool):
    """Tool for searching Confluence pages using keywords within a specified space."""

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # Get parameters
        keyword = tool_parameters.get("keyword")
        space_key = tool_parameters.get("spaceKey")

        if not keyword or not space_key:
            yield self.create_text_message(text="Keyword and space key are required")
            return

        # Get credentials
        base_url = self.runtime.credentials.get('baseUrl')
        username = self.runtime.credentials.get('userName')
        password = self.runtime.credentials.get('password')

        if not all([base_url, username, password]):
            yield self.create_text_message(text="Missing required credentials")
            return

        # Initialize session
        session = ConfluenceSession(base_url, username, password)

        try:
            # Construct search URL
            search_url = f"{session.base_api_url}/content/search"
            params = {
                'cql': f'space="{space_key}" AND text ~ "{keyword}"',
                'expand': 'version,space',
                'limit': 20  # Limit results to 20 pages
            }

            # Make API request
            response = session.session.get(
                search_url, params=params, headers=session.headers)

            if response.status_code == 200:
                results = response.json()
                pages = results.get('results', [])

                if not pages:
                    yield self.create_json_message({
                        "success": True,
                        "message": "No matching pages found",
                        "results": []
                    })
                    return

                # Format results
                formatted_results = []
                for page in pages:
                    formatted_results.append({
                        "id": page.get('id'),
                        "title": page.get('title'),
                        "type": page.get('type'),
                        "space": page.get('space', {}).get('key'),
                        "version": page.get('version', {}).get('number'),
                        "url": f"{base_url}/pages/viewpage.action?pageId={page.get('id')}"
                    })

                yield self.create_json_message({
                    "success": True,
                    "message": f"Found {len(formatted_results)} matching pages",
                    "results": formatted_results
                })
            else:
                yield self.create_json_message({
                    "success": False,
                    "message": f"Search failed with status code: {response.status_code}",
                    "details": response.text
                })

        except Exception as e:
            yield self.create_json_message({
                "success": False,
                "message": "Search request failed",
                "details": str(e)
            })
