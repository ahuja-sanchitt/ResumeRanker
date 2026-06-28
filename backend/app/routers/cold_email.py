"""Cold-email co-pilot endpoints.

  POST /contacts          -> discover engineering-lead contacts at a company (Apollo.io)
  POST /cold-email/draft  -> generate a tailored email from the résumé (multipart)
  POST /gmail/draft       -> create the email as a Gmail draft (never sends)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from app.models.schemas import (
    ColdEmailDraftResponse,
    ContactsRequest,
    ContactsResponse,
    GmailDraftRequest,
    GmailDraftResponse,
)
from app.services import gmail, gmail_session, llm
from app.services.apollo import ApolloError
from app.services.apollo import find_contacts as apollo_find_contacts
from app.services.hunter import domain_candidates
from app.services.pdf_extract import PdfExtractionError, extract_text_from_pdf
from app.services.rate_limit import limiter

logger = logging.getLogger("contacts")

CONTACTS_LIMIT = 6

router = APIRouter(tags=["cold-email"])

MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post("/contacts", response_model=ContactsResponse)
@limiter.limit("5/minute")
def contacts(request: Request, req: ContactsRequest) -> ContactsResponse:
    company = req.company.strip()
    candidates = domain_candidates(company)
    domain = candidates[0] if candidates else company.lower().replace(" ", "") + ".com"

    # Real contacts only (Apollo, India-filtered). If Apollo finds none, return an
    # empty list — the UI shows an honest empty state + manual entry. We never
    # fabricate contacts, since their emails would be guesses that bounce.
    try:
        result = apollo_find_contacts(company, candidates)
        contacts_list = result.get("contacts", [])[:CONTACTS_LIMIT]
        domain = result.get("domain") or domain
        logger.info("apollo returned %d contacts for company=%r", len(contacts_list), company)
    except ApolloError as exc:
        if "not configured" in str(exc).lower():
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        logger.warning("apollo failed for %r: %s", company, exc)
        contacts_list = []

    return ContactsResponse(company=company, domain=domain, contacts=contacts_list)


@router.post("/cold-email/draft", response_model=ColdEmailDraftResponse)
@limiter.limit("10/minute")
async def cold_email_draft(
    request: Request,
    resume: UploadFile = File(...),
    company: str = Form(...),
    contact_name: str = Form(""),
    contact_role: str = Form(""),
    jd: str = Form(""),
) -> ColdEmailDraftResponse:
    data = await resume.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="Résumé PDF exceeds the 10 MB limit.")
    try:
        resume_text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        draft = llm.draft_cold_email(
            resume_text, company.strip(), contact_name.strip(), contact_role.strip(), jd.strip()
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Draft generation failed: {exc}") from exc
    return ColdEmailDraftResponse(**draft)


@router.post("/gmail/draft", response_model=GmailDraftResponse)
@limiter.limit("20/minute")
def gmail_draft(
    request: Request, req: GmailDraftRequest, x_gmail_session: str | None = Header(default=None)
) -> GmailDraftResponse:
    if not x_gmail_session:
        raise HTTPException(status_code=401, detail="Connect Gmail first.")
    try:
        access_token = gmail_session.get_valid_access_token(x_gmail_session)
    except LookupError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        result = gmail.create_draft(access_token, req.to.strip(), req.subject, req.body)
    except gmail.GmailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GmailDraftResponse(**result)
