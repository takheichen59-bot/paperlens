"""Abstract contracts only: no network, parser or extractor implementation."""
from abc import ABC, abstractmethod
from pathlib import Path
from .models import (DownloadArtifact, ExtractionResult, PaperMeta, PaperQuery,
                     PaperRef, ParsedPaper)


class BaseFetcher(ABC):
    @abstractmethod
    async def search(self, query: PaperQuery) -> tuple[PaperRef, ...]:
        """Return bounded, ordered search matches."""
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, doi_or_id: str) -> PaperMeta:
        """Resolve exactly one paper; ambiguous inputs must raise an error."""
        raise NotImplementedError

    @abstractmethod
    async def download(self, meta: PaperMeta, destination: Path) -> DownloadArtifact:
        """Download a validated PDF to destination."""
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        """Release source resources."""
        raise NotImplementedError


class BaseParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: Path) -> ParsedPaper:
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, parsed_paper: ParsedPaper) -> ExtractionResult:
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError
