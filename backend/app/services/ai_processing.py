"""Trusted Phase 9B-1 processing pipeline; it never changes application stages."""

from dataclasses import dataclass
import logging
from uuid import UUID

import httpx

from app.ai.gemini import GeminiConfigurationError, GeminiProvider, GeminiProviderError
from app.ai.pdf_extraction import PDFExtractionError, extract_pdf_text
from app.ai.summary_contract import AIContractError, build_ai_summary_prompt, parse_provider_summary
from app.core.config import Settings
from app.schemas.recruiter_ai_summary import AIContextResponse
from app.services.candidate_cvs import MAX_CV_BYTES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIWorkItem:
    application_id: str; job_id: str; cv_id: str; job_title: str; job_requirements: str; cv_storage_path: str; cv_filename: str; cv_file_size_bytes: int


class AIProcessingOperationError(Exception): pass


class AIProcessingService:
    def __init__(self, client, provider: GeminiProvider): self.client, self.provider = client, provider

    def resolve_work_item(self, application_id: UUID) -> AIWorkItem:
        try:
            row = self.client.resolve_ai_work_item(str(application_id))
            if row.get("cv_mime_type") != "application/pdf" or not isinstance(row.get("cv_file_size_bytes"), int) or not 0 < row["cv_file_size_bytes"] <= MAX_CV_BYTES: raise ValueError("unsafe CV metadata")
            return AIWorkItem(str(row["id"]), str(row["job_id"]), str(row["cv_id"]), str(row["job_title"]), str(row["job_requirements"]), str(row["cv_storage_path"]), str(row["cv_filename"]), row["cv_file_size_bytes"])
        except (LookupError, KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise AIProcessingOperationError("AI work item is unavailable") from error

    def prepare_context(self, application_id: UUID) -> AIContextResponse:
        """Resolve the immutable CV snapshot and build the existing safe prompt."""
        item = self.resolve_work_item(application_id)
        try:
            content = self.client.download_candidate_cv(item.cv_storage_path)
            if not isinstance(content, bytes) or len(content) != item.cv_file_size_bytes:
                raise PDFExtractionError("CV object failed validation")
            prompt = build_ai_summary_prompt(
                job_title=item.job_title,
                job_requirements=item.job_requirements,
                cv_text=extract_pdf_text(content),
            )
            return AIContextResponse(application_id=item.application_id, prompt=prompt)
        except (PDFExtractionError, KeyError, TypeError, ValueError, httpx.HTTPError) as error:
            raise AIProcessingOperationError("AI context is unavailable") from error

    def process(self, application_id: UUID) -> None:
        try:
            context = self.prepare_context(application_id)
            summary = parse_provider_summary(self.provider.generate_summary(context.prompt))
            self.client.save_ai_summary_result(str(context.application_id), "completed", summary.profile_summary, summary.requirements_analysis.requirements_mentioned, summary.requirements_analysis.requirements_not_found, summary.interview_questions, None)
        except Exception as error:
            # Only category labels are logged: never prompts, CV/provider content, or credentials.
            logger.warning("AI summary processing handled failure category=%s", self._failure_category(error))
            try: self.client.save_ai_summary_result(str(application_id), "failed", None, None, None, None, "AI summary processing is unavailable")
            except (KeyError, TypeError, ValueError, httpx.HTTPError) as save_error: raise AIProcessingOperationError("AI summary processing is unavailable") from save_error

    @staticmethod
    def _failure_category(error: Exception) -> str:
        if isinstance(error, PDFExtractionError): return "pdf_extraction"
        if isinstance(error, GeminiProviderError): return error.category
        if isinstance(error, AIContractError): return "contract_validation"
        if isinstance(error, AIProcessingOperationError): return "work_item"
        if isinstance(error, httpx.HTTPError): return "provider_http"
        return "unexpected"


def build_ai_processing_service(client, settings: Settings) -> AIProcessingService:
    return AIProcessingService(client, GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_seconds))
