from pydantic import BaseModel, Field
from typing import Optional, List

class LegalDocumentPayload(BaseModel):
    doc_id: str = Field(..., description="Unique document ID")
    chunk_id: str = Field(..., description="Unique chunk sequence ID within document")
    source_type: str = Field(..., description="Type of source: 'laws', 'cases', 'course_notes', 'exam_bank'")
    title: str = Field(..., description="Document title or file name")
    section_type: Optional[str] = Field(None, description="Section or chapter classification")
    topic: Optional[str] = Field(None, description="Primary legal topic")
    issue_tag: Optional[str] = Field(None, description="Specific legal issue tag")
    law_name: Optional[str] = Field(None, description="Name of the law referenced")
    article_no: Optional[str] = Field(None, description="Article number of the law referenced")
    case_id: Optional[str] = Field(None, description="Court case ID / word character ID")
    court_level: Optional[str] = Field(None, description="Level of the deciding court")
    effective_date: Optional[str] = Field(None, description="Effective date of law or judgment date")
    version: Optional[str] = Field(None, description="Revision version / year")
    language: str = Field("zh-TW", description="Document language")
    ocr_confidence: Optional[float] = Field(None, description="Confidence score if extracted via OCR")
    stt_confidence: Optional[float] = Field(None, description="Confidence score if extracted via Whisper/Gemini STT")
    review_status: str = Field("draft", description="Review status: draft, approved, revised")
    source_path: str = Field(..., description="Original path or URL of source file")
    created_at: str = Field(..., description="Creation date timestamp")
    text: str = Field(..., description="Actual text chunk contents")

# Schema helper to get properties as list/dict
def get_payload_fields():
    return list(LegalDocumentPayload.__fields__.keys())
