"""
LinkedIn job scraping tools with search and detail extraction.

Uses innerText extraction for resilient job data capture.
"""

import logging
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from linkedin_mcp_server.constants import TOOL_TIMEOUT_SECONDS
from linkedin_mcp_server.core.exceptions import AuthenticationError
from linkedin_mcp_server.dependencies import get_ready_extractor, handle_auth_error
from linkedin_mcp_server.error_handler import raise_tool_error

logger = logging.getLogger(__name__)


def register_job_tools(mcp: FastMCP) -> None:
    """Register all job-related tools with the MCP server."""

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Get Job Details",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"job", "scraping"},
        exclude_args=["extractor"],
    )
    async def get_job_details(
        job_id: str,
        ctx: Context,
        extractor: Any | None = None,
    ) -> dict[str, Any]:
        """
        Get job details for a specific job posting on LinkedIn.

        Args:
            job_id: LinkedIn job ID (e.g., "4252026496", "3856789012")
            ctx: FastMCP context for progress reporting

        Returns:
            Dict with url, sections (name -> raw text), and optional references.
            The LLM should parse the raw text to extract job details.
        """
        try:
            extractor = extractor or await get_ready_extractor(
                ctx, tool_name="get_job_details"
            )
            logger.info("Scraping job: %s", job_id)

            await ctx.report_progress(
                progress=0, total=100, message="Starting job scrape"
            )

            result = await extractor.scrape_job(job_id)

            await ctx.report_progress(progress=100, total=100, message="Complete")

            return result

        except AuthenticationError as e:
            try:
                await handle_auth_error(e, ctx)
            except Exception as relogin_exc:
                raise_tool_error(relogin_exc, "get_job_details")
        except Exception as e:
            raise_tool_error(e, "get_job_details")  # NoReturn

    @mcp.tool(
        timeout=TOOL_TIMEOUT_SECONDS,
        title="Search Jobs",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"job", "search"},
        exclude_args=["extractor"],
    )
    async def search_jobs(
        ctx: Context,
        scrape_url: str | None = None,
        keywords: str | None = None,
        location: str | None = None,
        max_pages: Annotated[int, Field(ge=1, le=10)] = 3,
        date_posted: str | None = None,
        job_type: str | None = None,
        experience_level: str | None = None,
        work_type: str | None = None,
        easy_apply: bool = False,
        sort_by: str | None = None,
        extractor: Any | None = None,
    ) -> dict[str, Any]:
        """
        Search for jobs on LinkedIn.

        Returns job_ids that can be passed to get_job_details for full info.
        """
        try:
            extractor = extractor or await get_ready_extractor(
                ctx, tool_name="search_jobs"
            )

            if not keywords and not scrape_url:
                raise ValueError("Either keywords or scrape_url must be provided")

            logger.info(
                "Searching jobs: keywords='%s', scrape_url='%s', location='%s', max_pages=%d",
                keywords,
                scrape_url,
                location,
                max_pages,
            )

            await ctx.report_progress(
                progress=0, total=100, message="Starting job search"
            )

            if scrape_url:
                result = await extractor.search_jobs(
                    scrape_url=scrape_url,
                    location=location,
                    max_pages=max_pages,
                )
            else:
                result = await extractor.search_jobs(
                    keywords=keywords,
                    location=location,
                    max_pages=max_pages,
                    date_posted=date_posted,
                    job_type=job_type,
                    experience_level=experience_level,
                    work_type=work_type,
                    easy_apply=easy_apply,
                    sort_by=sort_by,
                )

            await ctx.report_progress(progress=100, total=100, message="Complete")
            return result

        except AuthenticationError as e:
            try:
                await handle_auth_error(e, ctx)
            except Exception as relogin_exc:
                raise_tool_error(relogin_exc, "search_jobs")
        except Exception as e:
            raise_tool_error(e, "search_jobs")  # NoReturn
