import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# backend 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag_system import RAGSystem


def create_test_app(mock_rag: MagicMock) -> FastAPI:
  """테스트용 FastAPI 앱 생성 (정적 파일 마운트 없음)"""
  from pydantic import BaseModel
  from typing import List, Optional

  app = FastAPI(title="Test App")

  class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

  class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str

  class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]

  @app.post("/api/query", response_model=QueryResponse)
  async def query_documents(request: QueryRequest):
    try:
      session_id = request.session_id
      if not session_id:
        session_id = mock_rag.session_manager.create_session()
      answer, sources = mock_rag.query(request.query, session_id)
      return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @app.get("/api/courses", response_model=CourseStats)
  async def get_course_stats():
    try:
      analytics = mock_rag.get_course_analytics()
      return CourseStats(
        total_courses=analytics["total_courses"],
        course_titles=analytics["course_titles"]
      )
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @app.delete("/api/sessions/{session_id}")
  async def delete_session(session_id: str):
    try:
      if session_id in mock_rag.session_manager.sessions:
        del mock_rag.session_manager.sessions[session_id]
      return {"status": "ok"}
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  return app


@pytest.fixture
def mock_rag_system():
  """RAGSystem mock 생성"""
  mock_rag = MagicMock(spec=RAGSystem)
  mock_rag.session_manager = MagicMock()
  mock_rag.session_manager.sessions = {}
  mock_rag.session_manager.create_session.return_value = "test-session-123"
  mock_rag.query.return_value = ("테스트 답변입니다.", ["source1.txt", "source2.txt"])
  mock_rag.get_course_analytics.return_value = {
    "total_courses": 3,
    "course_titles": ["AI 기초", "딥러닝 입문", "LLM 활용"]
  }
  return mock_rag


@pytest.fixture
def test_client(mock_rag_system):
  """FastAPI TestClient 생성"""
  app = create_test_app(mock_rag_system)
  return TestClient(app)
