"""
Gradient AI Platform Tools Module

Exposes DigitalOcean Gradient AI features as MCP tools:
- Knowledge Base query (RAG with citations)
- AI Agent chat
- List knowledge bases and agents

Requires: pip install gradient (official DigitalOcean SDK)

Author: Luke Steuber

Example:
    from tools import get_registry
    from tools.gradient_tools import GradientToolModule

    # Register tools
    module = GradientToolModule()
    module.register_with_registry()

    # Use via registry
    registry = get_registry()
    result = await registry.call_tool('gradient_query_kb', {
        'kb_id': 'uuid-here',
        'query': 'What is the return policy?'
    })
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional

from .module_base import ToolModuleBase

logger = logging.getLogger(__name__)


class GradientToolModule(ToolModuleBase):
    """
    Tool module for DigitalOcean Gradient AI Platform features.

    Provides tools for:
    - Knowledge Base queries (RAG with citations)
    - AI Agent conversations
    - Resource listing

    Requires GRADIENT_API_KEY environment variable.
    """

    name = "gradient"
    display_name = "Gradient AI Tools"
    description = "DigitalOcean Gradient AI Platform - Knowledge Bases and Agents"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Gradient tools module.

        Args:
            config: Optional configuration with:
                - api_key: Gradient API key (or use env var)
                - management_token: DigitalOcean token for management ops
        """
        self._provider = None
        super().__init__(config)

    def initialize(self):
        """Initialize tool schemas."""
        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "gradient_query_kb",
                    "description": "Query a Gradient Knowledge Base using RAG (Retrieval Augmented Generation). Returns relevant passages with citations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "kb_id": {
                                "type": "string",
                                "description": "Knowledge Base UUID"
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query or question"
                            },
                            "num_results": {
                                "type": "integer",
                                "default": 5,
                                "description": "Number of results to return (1-20)"
                            }
                        },
                        "required": ["kb_id", "query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gradient_agent_chat",
                    "description": "Chat with a Gradient AI Agent. Agents are configured assistants with specific capabilities and knowledge.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Agent UUID"
                            },
                            "message": {
                                "type": "string",
                                "description": "User message to send to the agent"
                            }
                        },
                        "required": ["agent_id", "message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gradient_list_knowledge_bases",
                    "description": "List all available Gradient Knowledge Bases",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gradient_list_agents",
                    "description": "List all available Gradient AI Agents",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gradient_complete",
                    "description": "Generate a chat completion using Gradient's serverless inference",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "messages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["role", "content"]
                                },
                                "description": "Conversation messages"
                            },
                            "model": {
                                "type": "string",
                                "default": "llama3.3-70b-instruct",
                                "description": "Model to use for completion"
                            },
                            "temperature": {
                                "type": "number",
                                "default": 0.7,
                                "description": "Sampling temperature (0-1)"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "default": 1024,
                                "description": "Maximum tokens to generate"
                            }
                        },
                        "required": ["messages"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gradient_list_models",
                    "description": "List available models on Gradient platform",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    @property
    def provider(self):
        """Lazy-load the Gradient provider."""
        if self._provider is None:
            try:
                from llm_providers import GradientProviderV2

                api_key = self.config.get('api_key') or os.getenv('GRADIENT_API_KEY')
                management_token = self.config.get('management_token') or os.getenv('DIGITALOCEAN_TOKEN')

                self._provider = GradientProviderV2(
                    api_key=api_key,
                    management_token=management_token
                )
            except ImportError:
                raise ImportError(
                    "GradientProviderV2 not available. Install do-gradient-ai package."
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gradient provider: {e}")

        return self._provider

    def gradient_query_kb(
        self,
        kb_id: str,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Query a Knowledge Base for relevant information.

        Args:
            kb_id: Knowledge Base UUID
            query: Search query or question
            num_results: Number of results to return

        Returns:
            Dict with results and citations
        """
        try:
            response = self.provider.query_knowledge_base(
                kb_id=kb_id,
                query=query,
                num_results=min(max(1, num_results), 20)
            )

            # Format response
            if hasattr(response, 'results'):
                results = []
                for r in response.results:
                    result = {
                        'content': getattr(r, 'content', str(r)),
                        'score': getattr(r, 'score', None),
                    }
                    if hasattr(r, 'metadata'):
                        result['metadata'] = r.metadata
                    if hasattr(r, 'citation'):
                        result['citation'] = r.citation
                    results.append(result)
                return {
                    'success': True,
                    'kb_id': kb_id,
                    'query': query,
                    'results': results
                }
            else:
                # Raw response
                return {
                    'success': True,
                    'kb_id': kb_id,
                    'query': query,
                    'raw_response': str(response)
                }

        except Exception as e:
            logger.error(f"KB query error: {e}")
            return {
                'success': False,
                'error': str(e),
                'kb_id': kb_id,
                'query': query
            }

    def gradient_agent_chat(
        self,
        agent_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Chat with an AI Agent.

        Args:
            agent_id: Agent UUID
            message: User message

        Returns:
            Dict with agent response
        """
        try:
            response = self.provider.agent_chat(
                agent_id=agent_id,
                messages=message
            )

            # Format response
            result = {
                'success': True,
                'agent_id': agent_id,
                'content': getattr(response, 'content', str(response))
            }

            if hasattr(response, 'citations'):
                result['citations'] = response.citations

            if hasattr(response, 'metadata'):
                result['metadata'] = response.metadata

            return result

        except Exception as e:
            logger.error(f"Agent chat error: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent_id': agent_id
            }

    def gradient_list_knowledge_bases(self) -> Dict[str, Any]:
        """
        List all available Knowledge Bases.

        Returns:
            Dict with list of knowledge bases
        """
        try:
            kbs = self.provider.list_knowledge_bases()

            # Format response
            if hasattr(kbs, '__iter__'):
                kb_list = []
                for kb in kbs:
                    kb_info = {
                        'id': getattr(kb, 'id', str(kb)),
                        'name': getattr(kb, 'name', 'Unknown'),
                    }
                    if hasattr(kb, 'description'):
                        kb_info['description'] = kb.description
                    if hasattr(kb, 'created_at'):
                        kb_info['created_at'] = str(kb.created_at)
                    kb_list.append(kb_info)

                return {
                    'success': True,
                    'knowledge_bases': kb_list,
                    'count': len(kb_list)
                }
            else:
                return {
                    'success': True,
                    'raw_response': str(kbs)
                }

        except Exception as e:
            logger.error(f"List KB error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def gradient_list_agents(self) -> Dict[str, Any]:
        """
        List all available AI Agents.

        Returns:
            Dict with list of agents
        """
        try:
            agents = self.provider.list_agents()

            # Format response
            if hasattr(agents, '__iter__'):
                agent_list = []
                for agent in agents:
                    agent_info = {
                        'id': getattr(agent, 'id', str(agent)),
                        'name': getattr(agent, 'name', 'Unknown'),
                    }
                    if hasattr(agent, 'description'):
                        agent_info['description'] = agent.description
                    if hasattr(agent, 'model'):
                        agent_info['model'] = agent.model
                    if hasattr(agent, 'created_at'):
                        agent_info['created_at'] = str(agent.created_at)
                    agent_list.append(agent_info)

                return {
                    'success': True,
                    'agents': agent_list,
                    'count': len(agent_list)
                }
            else:
                return {
                    'success': True,
                    'raw_response': str(agents)
                }

        except Exception as e:
            logger.error(f"List agents error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def gradient_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "llama3.3-70b-instruct",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Generate a chat completion.

        Args:
            messages: List of message dicts with role and content
            model: Model ID
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with completion response
        """
        try:
            from llm_providers import Message

            # Convert to Message objects
            msg_objects = [
                Message(role=m['role'], content=m['content'])
                for m in messages
            ]

            response = self.provider.complete(
                messages=msg_objects,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return self._format_completion_response(response)

        except Exception as e:
            logger.error(f"Completion error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def gradient_list_models(self) -> Dict[str, Any]:
        """
        List available models.

        Returns:
            Dict with list of model IDs
        """
        try:
            models = self.provider.list_models()

            return {
                'success': True,
                'models': models,
                'count': len(models)
            }

        except Exception as e:
            logger.error(f"List models error: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def register_gradient_tools(registry=None) -> Dict[str, Any]:
    """
    Register Gradient tools with the tool registry.

    Args:
        registry: ToolRegistry instance (uses global if None)

    Returns:
        Registration result
    """
    try:
        module = GradientToolModule()
        return module.register_with_registry(registry)
    except Exception as e:
        logger.warning(f"Failed to register Gradient tools: {e}")
        return {"success": False, "error": str(e)}


# Allow running as standalone script
if __name__ == '__main__':
    GradientToolModule.main()
