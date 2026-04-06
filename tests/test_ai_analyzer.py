"""
Unit tests for AI analyzer module.
"""

import pytest
import json
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.video_agent.core.ai_analyzer import MCPResponseParser


class TestMCPResponseParser:
    """Test cases for MCP response parser."""
    
    def test_parse_standard_format(self):
        """Test parsing standard MCP response format."""
        response = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "description": "A person walking in the park",
                            "tags": ["daily_activity"]
                        })
                    }
                ]
            }
        }
        
        result = MCPResponseParser.parse(response)
        
        assert result['description'] == "A person walking in the park"
        assert result['tags'] == ["daily_activity"]
        assert result['confidence_scores'] is None
    
    def test_parse_error_response(self):
        """Test parsing MCP error response."""
        response = {
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            }
        }
        
        result = MCPResponseParser.parse(response)
        
        assert "MCP Error" in result['description']
        assert result['tags'] == []
        assert result['confidence_scores'] is None
    
    def test_parse_plain_text_response(self):
        """Test parsing plain text response."""
        response = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "This is a plain text description"
                    }
                ]
            }
        }
        
        result = MCPResponseParser.parse(response)
        
        assert result['description'] == "This is a plain text description"
        assert result['tags'] == []
    
    def test_parse_missing_result_field(self):
        """Test parsing response with missing result field."""
        response = {
            "jsonrpc": "2.0",
            "id": 1
        }
        
        result = MCPResponseParser.parse(response)
        
        assert "No result" in result['description']
        assert result['tags'] == []
    
    def test_parse_missing_content_field(self):
        """Test parsing response with missing content field."""
        response = {
            "result": {}
        }
        
        result = MCPResponseParser.parse(response)
        
        assert result['description'] == "Empty result"
        assert result['tags'] == []
    
    def test_parse_empty_content_array(self):
        """Test parsing response with empty content array."""
        response = {
            "result": {
                "content": []
            }
        }
        
        result = MCPResponseParser.parse(response)
        
        assert "No text content" in result['description']
        assert result['tags'] == []
    
    def test_parse_multiple_content_items(self):
        """Test parsing response with multiple content items."""
        response = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "First part"
                    },
                    {
                        "type": "text",
                        "text": "Second part"
                    }
                ]
            }
        }
        
        result = MCPResponseParser.parse(response)
        
        assert "First part" in result['description']
        assert "Second part" in result['description']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
