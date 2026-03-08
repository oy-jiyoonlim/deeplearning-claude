import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- You may use tools multiple times per query when needed (e.g., get course outline first, then search specific content)
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Course Outline Tool Usage:
- When asked about course overview, structure, lesson list, or course composition → use `get_course_outline`
- Include the course title, course link, and all lesson numbers with titles in your response

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str, max_tool_rounds: int = 2):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tool_rounds = max_tool_rounds

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def _extract_text(self, response) -> str:
        """응답에서 텍스트 블록 추출"""
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text
        return ""

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return self._extract_text(response)

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        루프 기반 다중 라운드 도구 호출 처리.

        Args:
            initial_response: 도구 호출을 포함한 초기 응답
            base_params: 기본 API 파라미터
            tool_manager: 도구 실행 매니저

        Returns:
            도구 실행 후 최종 응답 텍스트
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for round in range(self.max_tool_rounds):
            # assistant 응답 추가
            messages.append({"role": "assistant", "content": current_response.content})

            # tool_use 블록 실행 + 에러 핸들링
            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool execution error: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            # 마지막 라운드에서는 tools 제외 → Claude가 반드시 텍스트로 응답
            is_last_round = (round == self.max_tool_rounds - 1)

            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            if not is_last_round and "tools" in base_params:
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = {"type": "auto"}

            next_response = self.client.messages.create(**next_params)

            # 도구 호출 없으면 종료
            if next_response.stop_reason != "tool_use" or is_last_round:
                return self._extract_text(next_response)

            current_response = next_response

        return self._extract_text(current_response)
