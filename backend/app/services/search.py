import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Set
from urllib.parse import urlencode

import httpx

from app.services.query_expander import expand_academic_queries

logger = logging.getLogger(__name__)


class SearchAPIError(Exception):
    pass


class SemanticScholarSearch:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    async def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_ids: Set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries[:6]:
                cleaned_query = self._clean_query(query)
                if not cleaned_query:
                    continue

                try:
                    papers = await self._search_single(
                        client,
                        cleaned_query,
                        year_from,
                        year_to,
                        limit,
                    )
                    for paper in papers:
                        paper_id = paper.get("externalId") or paper.get("paperId")
                        if paper_id and paper_id not in seen_ids:
                            seen_ids.add(paper_id)
                            all_papers.append(self._parse_paper(paper, "semantic_scholar"))
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    logger.warning(
                        "Semantic Scholar search failed for query '%s': HTTP %s",
                        cleaned_query,
                        status,
                    )
                    if status == 429:
                        await asyncio.sleep(2.0)
                    continue
                except Exception as e:
                    logger.warning("Semantic Scholar search failed for query '%s': %s", cleaned_query, e)
                    continue

        return all_papers

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: str,
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        params = {
            "query": query,
            "year": f"{year_from}-{year_to}",
            "limit": min(limit, 100),
            "fields": "paperId,title,authors,year,abstract,venue,citationCount,url,externalId",
        }
        headers = {"Accept": "application/json"}

        response = await client.get(f"{self.BASE_URL}/paper/search", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def _parse_paper(self, paper: Dict, source: str) -> Dict:
        authors = []
        if paper.get("authors"):
            authors = [author.get("name", "Unknown") for author in paper["authors"][:10]]

        return {
            "external_id": paper.get("externalId") or paper.get("paperId"),
            "title": paper.get("title", "Untitled"),
            "authors": authors,
            "year": paper.get("year"),
            "abstract": paper.get("abstract"),
            "venue": paper.get("venue"),
            "citation_count": paper.get("citationCount", 0),
            "url": paper.get("url"),
            "source": source,
        }

    def _clean_query(self, query: str) -> str:
        query = re.sub(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b", " ", query or "")
        query = re.sub(r"\b(19|20)\d{2}\b", " ", query)
        query = re.sub(r"\s+", " ", query).strip(" -")
        return query


class ArxivSearch:
    BASE_URL = "http://export.arxiv.org/api/query"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_ids: Set[str] = set()
        request_count = 0

        with httpx.Client(timeout=httpx.Timeout(4.0, connect=2.0), follow_redirects=True) as client:
            for query in queries:
                if self._contains_chinese(query):
                    continue

                for arxiv_query in self._build_query_variants(query):
                    request_count += 1
                    if request_count > 2:
                        return all_papers

                    try:
                        papers = self._search_single(client, arxiv_query, year_from, year_to, limit)
                    except Exception as e:
                        logger.warning("arXiv search failed for query '%s': %s", arxiv_query, e)
                        continue

                    for paper in papers:
                        external_id = paper.get("external_id")
                        if external_id and external_id not in seen_ids:
                            seen_ids.add(external_id)
                            all_papers.append(paper)

                    if len(all_papers) >= limit:
                        return all_papers

        return all_papers

    def _search_single(
        self,
        client: httpx.Client,
        arxiv_query: str,
        year_from: int,
        year_to: int,
        limit: int,
    ) -> List[Dict]:
        params = {
            "search_query": arxiv_query,
            "sortBy": "relevance",
            "sortOrder": "descending",
            "start": 0,
            "max_results": min(max(limit, 20), 50),
        }
        url = f"{self.BASE_URL}?{urlencode(params)}"
        logger.info("arXiv query: %s", arxiv_query)

        response = client.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        papers = []
        for entry in root.findall("atom:entry", self.ATOM_NS):
            paper = self._parse_entry(entry)
            year = paper.get("year")
            if year and not (year_from <= year <= year_to):
                continue
            papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> Dict:
        def find_text(path: str) -> str:
            node = entry.find(path, self.ATOM_NS)
            return (node.text or "").strip() if node is not None else ""

        entry_id = find_text("atom:id")
        title = re.sub(r"\s+", " ", find_text("atom:title"))
        summary = re.sub(r"\s+", " ", find_text("atom:summary"))
        published = find_text("atom:published")
        year = None
        if published[:4].isdigit():
            year = int(published[:4])

        authors = []
        for author in entry.findall("atom:author", self.ATOM_NS)[:10]:
            name = author.find("atom:name", self.ATOM_NS)
            if name is not None and name.text:
                authors.append(name.text.strip())

        return {
            "external_id": entry_id,
            "title": title or "Untitled",
            "authors": authors,
            "year": year,
            "abstract": summary,
            "venue": "arXiv",
            "citation_count": 0,
            "url": entry_id,
            "source": "arxiv",
        }

    def _build_query_variants(self, query: str) -> List[str]:
        tokens = self._tokens(query)
        if not tokens:
            return []

        variants = []
        core = tokens[:4]
        if len(core) >= 2:
            variants.append(" AND ".join([f"all:{token}" for token in core]))

        if len(tokens) >= 3:
            broader = self._broaden_tokens(tokens)
            if len(broader) >= 2:
                variants.append(" AND ".join([f"all:{token}" for token in broader[:3]]))

        if len(tokens) >= 2:
            variants.append(" OR ".join([f"ti:{token}" for token in tokens[:4]]))

        return self._unique(variants)

    def _tokens(self, query: str) -> List[str]:
        normalized = (query or "").replace("-", " ")
        raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9]*", normalized.lower())
        stopwords = {
            "a", "an", "and", "the", "of", "in", "on", "to", "for", "with", "by",
            "from", "using", "use", "based", "via", "towards", "toward",
            "survey", "surveys", "review", "reviews", "benchmark", "benchmarks",
            "dataset", "datasets", "evaluation", "metrics", "applications",
            "advances", "approach", "approaches", "method", "methods", "task",
            "tasks", "system", "systems", "training", "learning",
        }
        return [token for token in raw_tokens if len(token) > 1 and token not in stopwords]

    def _broaden_tokens(self, tokens: List[str]) -> List[str]:
        priority = [
            "retrieval", "augmented", "generation", "language", "model", "models",
            "multimodal", "vision", "transparent", "object", "depth", "completion",
        ]
        selected = [token for token in priority if token in tokens]
        if len(selected) >= 2:
            return selected
        return tokens[:3]

    def _contains_chinese(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

    def _unique(self, items: List[str]) -> List[str]:
        result = []
        seen = set()
        for item in items:
            if item and item not in seen:
                result.append(item)
                seen.add(item)
        return result


class OpenAlexSearch:
    BASE_URL = "https://api.openalex.org/works"

    async def search(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_ids: Set[str] = set()

        async with httpx.AsyncClient(timeout=20.0) as client:
            for query in queries[:6]:
                cleaned_query = self._clean_query(query)
                if not cleaned_query:
                    continue

                try:
                    papers = await self._search_single(client, cleaned_query, year_from, year_to, limit)
                    for paper in papers:
                        external_id = paper.get("external_id")
                        if external_id and external_id not in seen_ids:
                            seen_ids.add(external_id)
                            all_papers.append(paper)

                    if len(all_papers) >= limit:
                        return all_papers
                except Exception as e:
                    logger.warning("OpenAlex search failed for query '%s': %s", cleaned_query, e)
                    continue

        return all_papers

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: str,
        year_from: int,
        year_to: int,
        limit: int,
    ) -> List[Dict]:
        params = {
            "search": query,
            "filter": (
                f"from_publication_date:{year_from}-01-01,"
                f"to_publication_date:{year_to}-12-31"
            ),
            "per-page": min(max(limit, 10), 50),
        }
        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return [self._parse_work(work) for work in data.get("results", [])]

    def _parse_work(self, work: Dict) -> Dict:
        authors = []
        for authorship in (work.get("authorships") or [])[:10]:
            author = authorship.get("author") or {}
            if author.get("display_name"):
                authors.append(author["display_name"])

        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        url = (
            primary_location.get("landing_page_url")
            or work.get("doi")
            or work.get("id")
        )

        return {
            "external_id": work.get("id") or work.get("doi"),
            "title": work.get("display_name") or "Untitled",
            "authors": authors,
            "year": work.get("publication_year"),
            "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index")),
            "venue": source.get("display_name") or "OpenAlex",
            "citation_count": work.get("cited_by_count") or 0,
            "url": url,
            "source": "openalex",
        }

    def _reconstruct_abstract(self, inverted_index: Dict | None) -> str | None:
        if not inverted_index:
            return None

        positions = []
        for word, indexes in inverted_index.items():
            for index in indexes:
                positions.append((index, word))

        positions.sort(key=lambda item: item[0])
        return " ".join(word for _, word in positions)

    def _clean_query(self, query: str) -> str:
        query = re.sub(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b", " ", query or "")
        query = re.sub(r"\b(19|20)\d{2}\b", " ", query)
        query = re.sub(r"\s+", " ", query).strip(" -")
        return query


class SearchService:
    def __init__(self):
        self.semantic_scholar = SemanticScholarSearch()
        self.arxiv = ArxivSearch()
        self.openalex = OpenAlexSearch()

    async def search_papers(
        self,
        queries: List[str],
        year_from: int,
        year_to: int,
        limit: int
    ) -> List[Dict]:
        all_papers = []
        seen_titles: Set[str] = set()
        expanded_queries = expand_academic_queries(queries)
        logger.info("Expanded search queries: %s", expanded_queries)

        try:
            arxiv_papers = await asyncio.to_thread(
                self.arxiv.search,
                expanded_queries,
                year_from,
                year_to,
                limit,
            )
            self._append_unique(all_papers, seen_titles, arxiv_papers)
        except Exception as e:
            logger.warning("arXiv search failed, will rely on Semantic Scholar: %s", e)

        if len(all_papers) < limit:
            try:
                openalex_papers = await self.openalex.search(
                    expanded_queries,
                    year_from,
                    year_to,
                    max(limit, limit - len(all_papers)),
                )
                self._append_unique(all_papers, seen_titles, openalex_papers)
            except Exception as e:
                logger.warning("OpenAlex search failed, will rely on Semantic Scholar: %s", e)

        if len(all_papers) < limit:
            try:
                ss_papers = await self.semantic_scholar.search(
                    expanded_queries,
                    year_from,
                    year_to,
                    max(limit, limit - len(all_papers)),
                )
                self._append_unique(all_papers, seen_titles, ss_papers)
            except Exception as e:
                logger.warning("Semantic Scholar search failed: %s", e)

        return all_papers[: max(limit * 2, limit)]

    def _append_unique(self, target: List[Dict], seen_titles: Set[str], papers: List[Dict]):
        for paper in papers:
            title_lower = paper.get("title", "").strip().lower()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                target.append(paper)


def get_search_service() -> SearchService:
    return SearchService()
