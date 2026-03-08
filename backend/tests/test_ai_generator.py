import pytest
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator


def make_text_block(text):
    """텍스트 콘텐츠 블록 mock 생성"""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(tool_id, name, input_data):
    """tool_use 콘텐츠 블록 mock 생성"""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    # text 속성 없음 → _extract_text에서 건너뜀
    del block.text
    return block


def make_response(stop_reason, content_blocks):
    """API 응답 mock 생성"""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


@pytest.fixture
def generator():
    """AIGenerator 인스턴스 생성 (mock client)"""
    with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        gen = AIGenerator(api_key="test-key", model="test-model", max_tool_rounds=2)
        yield gen, mock_client


class TestDirectResponse:
    """도구 없이 직접 응답"""

    def test_returns_text_without_tools(self, generator):
        gen, mock_client = generator
        response = make_response("end_turn", [make_text_block("안녕하세요")])
        mock_client.messages.create.return_value = response

        result = gen.generate_response("테스트 질문")

        assert result == "안녕하세요"
        assert mock_client.messages.create.call_count == 1


class TestSingleRoundToolCall:
    """단일 라운드 도구 호출"""

    def test_single_tool_call(self, generator):
        gen, mock_client = generator
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "검색 결과 데이터"

        # 첫 번째: tool_use 응답, 두 번째: 최종 텍스트 응답
        tool_response = make_response("tool_use", [
            make_tool_use_block("tool_1", "search_course_content", {"query": "테스트"})
        ])
        final_response = make_response("end_turn", [make_text_block("최종 답변")])
        mock_client.messages.create.side_effect = [tool_response, final_response]

        result = gen.generate_response(
            "테스트 질문",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert result == "최종 답변"
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with("search_course_content", query="테스트")


class TestMultiRoundToolCall:
    """2라운드 순차 도구 호출"""

    def test_two_round_tool_calls(self, generator):
        gen, mock_client = generator
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["outline 결과", "content 결과"]

        # 초기: tool_use, 2차: tool_use, 3차: 최종 텍스트
        first_tool = make_response("tool_use", [
            make_tool_use_block("tool_1", "get_course_outline", {"course_name": "AI 기초"})
        ])
        second_tool = make_response("tool_use", [
            make_tool_use_block("tool_2", "search_course_content", {"query": "레슨 4 주제"})
        ])
        final_response = make_response("end_turn", [make_text_block("종합 답변")])
        mock_client.messages.create.side_effect = [first_tool, second_tool, final_response]

        result = gen.generate_response(
            "복합 질문",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert result == "종합 답변"
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # 두 번째 호출에는 첫 번째 결과가 메시지에 포함되어야 함
        second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        # assistant + tool_result 메시지가 포함되어 있어야 함
        assert len(second_call_messages) >= 3  # user + assistant + tool_result


class TestMaxRoundsEnforcement:
    """최대 라운드 초과 시 강제 종료"""

    def test_last_round_excludes_tools(self, generator):
        gen, mock_client = generator
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["결과1", "결과2"]

        # 2라운드 모두 tool_use를 시도하는 시나리오
        first_tool = make_response("tool_use", [
            make_tool_use_block("tool_1", "search_course_content", {"query": "q1"})
        ])
        second_tool = make_response("tool_use", [
            make_tool_use_block("tool_2", "search_course_content", {"query": "q2"})
        ])
        # 마지막 라운드에서는 tools 없이 호출되므로 텍스트 응답
        final_response = make_response("end_turn", [make_text_block("강제 종료 답변")])
        mock_client.messages.create.side_effect = [first_tool, second_tool, final_response]

        result = gen.generate_response(
            "질문",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert result == "강제 종료 답변"

        # 마지막 API 호출(3번째)에는 tools 파라미터가 없어야 함
        last_call_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in last_call_kwargs
        assert "tool_choice" not in last_call_kwargs

        # 첫 번째 후속 호출(2번째)에는 tools 파라미터가 있어야 함
        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        assert "tools" in second_call_kwargs


class TestToolExecutionError:
    """도구 실행 에러 처리"""

    def test_tool_error_returns_error_string(self, generator):
        gen, mock_client = generator
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB 연결 실패")

        tool_response = make_response("tool_use", [
            make_tool_use_block("tool_1", "search_course_content", {"query": "test"})
        ])
        final_response = make_response("end_turn", [make_text_block("에러 대응 답변")])
        mock_client.messages.create.side_effect = [tool_response, final_response]

        result = gen.generate_response(
            "질문",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert result == "에러 대응 답변"

        # tool_result에 에러 문자열이 포함되어야 함
        second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_msg = second_call_messages[-1]  # 마지막 메시지가 tool_result
        assert tool_result_msg["role"] == "user"
        assert "Tool execution error: DB 연결 실패" in tool_result_msg["content"][0]["content"]


class TestConversationHistory:
    """대화 히스토리 포함"""

    def test_history_included_in_system_prompt(self, generator):
        gen, mock_client = generator
        response = make_response("end_turn", [make_text_block("답변")])
        mock_client.messages.create.return_value = response

        gen.generate_response("질문", conversation_history="이전 대화 내용")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "이전 대화 내용" in call_kwargs["system"]
        assert "Previous conversation:" in call_kwargs["system"]
