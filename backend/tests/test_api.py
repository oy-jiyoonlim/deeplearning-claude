import pytest
from unittest.mock import MagicMock


class TestQueryEndpoint:
  """POST /api/query 엔드포인트 테스트"""

  def test_query_with_session_id(self, test_client, mock_rag_system):
    """세션 ID가 있는 쿼리 요청"""
    response = test_client.post("/api/query", json={
      "query": "AI란 무엇인가요?",
      "session_id": "existing-session"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "테스트 답변입니다."
    assert data["sources"] == ["source1.txt", "source2.txt"]
    assert data["session_id"] == "existing-session"
    mock_rag_system.query.assert_called_once_with("AI란 무엇인가요?", "existing-session")

  def test_query_without_session_id(self, test_client, mock_rag_system):
    """세션 ID 없이 쿼리 → 자동 생성"""
    response = test_client.post("/api/query", json={
      "query": "딥러닝이란?"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    mock_rag_system.session_manager.create_session.assert_called_once()

  def test_query_missing_field(self, test_client):
    """필수 필드 누락 시 422 에러"""
    response = test_client.post("/api/query", json={})
    assert response.status_code == 422

  def test_query_internal_error(self, test_client, mock_rag_system):
    """RAGSystem 에러 시 500 응답"""
    mock_rag_system.query.side_effect = RuntimeError("DB 연결 실패")

    response = test_client.post("/api/query", json={
      "query": "테스트",
      "session_id": "s1"
    })

    assert response.status_code == 500
    assert "DB 연결 실패" in response.json()["detail"]


class TestCoursesEndpoint:
  """GET /api/courses 엔드포인트 테스트"""

  def test_get_courses(self, test_client, mock_rag_system):
    """코스 목록 정상 조회"""
    response = test_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 3
    assert len(data["course_titles"]) == 3
    assert "AI 기초" in data["course_titles"]

  def test_get_courses_error(self, test_client, mock_rag_system):
    """코스 조회 에러 시 500 응답"""
    mock_rag_system.get_course_analytics.side_effect = Exception("ChromaDB 에러")

    response = test_client.get("/api/courses")

    assert response.status_code == 500
    assert "ChromaDB 에러" in response.json()["detail"]


class TestSessionEndpoint:
  """DELETE /api/sessions/{session_id} 엔드포인트 테스트"""

  def test_delete_existing_session(self, test_client, mock_rag_system):
    """존재하는 세션 삭제"""
    mock_rag_system.session_manager.sessions = {"sess-1": MagicMock()}

    response = test_client.delete("/api/sessions/sess-1")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "sess-1" not in mock_rag_system.session_manager.sessions

  def test_delete_nonexistent_session(self, test_client, mock_rag_system):
    """존재하지 않는 세션 삭제 시에도 200 반환"""
    mock_rag_system.session_manager.sessions = {}

    response = test_client.delete("/api/sessions/unknown-id")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
