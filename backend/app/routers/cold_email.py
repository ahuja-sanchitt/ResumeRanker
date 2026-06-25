"""Cold-email co-pilot endpoints.

  POST /contacts          -> discover EM/senior-dev contacts at a company (Hunter.io)
  POST /cold-email/draft  -> generate a tailored email from the résumé (multipart)
  POST /gmail/draft       -> create the email as a Gmail draft (never sends)
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from app.models.schemas import (
    ColdEmailDraftResponse,
    ContactsRequest,
    ContactsResponse,
    GmailDraftRequest,
    GmailDraftResponse,
)
import logging

from app.services import gmail, gmail_session, llm
from app.services.apollo import ApolloError
from app.services.apollo import find_contacts as apollo_find_contacts
from app.services.fallback_contacts import generate_contacts
from app.services.hunter import domain_candidates
from app.services.pdf_extract import PdfExtractionError, extract_text_from_pdf
from app.services.rate_limit import limiter

logger = logging.getLogger("contacts")

CONTACTS_TARGET = 5

router = APIRouter(tags=["cold-email"])

MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post("/contacts", response_model=ContactsResponse)
@limiter.limit("5/minute")
def contacts(request: Request, req: ContactsRequest) -> ContactsResponse:
    company = req.company.strip()
    candidates = domain_candidates(company)
    domain = candidates[0] if candidates else company.lower().replace(" ", "") + ".com"

    # --- Try Apollo (real contacts, India-filtered) ---
    apollo_contacts: list = []
    try:
        result = apollo_find_contacts(company, candidates)
        apollo_contacts = result.get("contacts", [])
        domain = result.get("domain") or domain
        logger.info("apollo returned %d contacts for company=%r", len(apollo_contacts), company)
    except ApolloError as exc:
        if "not configured" not in str(exc).lower():
            logger.warning("apollo failed for %r: %s", company, exc)

    # --- Always return exactly CONTACTS_TARGET contacts ---
    # Fill any shortfall with randomly generated ones so the user always has options.
    shortfall = CONTACTS_TARGET - len(apollo_contacts)
    generated = generate_contacts(domain, count=shortfall) if shortfall > 0 else []
    if generated:
        logger.info("contacts filling %d generated contacts for domain=%r", len(generated), domain)

    final_contacts = (apollo_contacts + generated)[:CONTACTS_TARGET]
    return ContactsResponse(company=company, domain=domain, contacts=final_contacts)


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
