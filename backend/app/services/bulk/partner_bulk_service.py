from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.schemas.partner import (
    PartnerBulkCreateRequest,
    PartnerBulkCreateResult,
    PartnerBulkError,
)


@dataclass
class _NormalizedPartnerRow:
    row_number: int
    partner_type: str
    name: str
    business_no: str
    is_active: bool


class PartnerBulkService:
    def create_bulk(
        self,
        db: Session,
        payload: PartnerBulkCreateRequest,
    ) -> PartnerBulkCreateResult:
        normalized_rows, errors = self._normalize_and_validate(payload.items)

        if normalized_rows:
            errors.extend(self._validate_duplicate_business_no_in_payload(normalized_rows))

        valid_rows = self._exclude_error_rows(normalized_rows, errors)

        if valid_rows:
            errors.extend(self._validate_duplicate_business_no_in_db(db, valid_rows))

        valid_rows = self._exclude_error_rows(valid_rows, errors)

        created_items: list[Partner] = []

        if valid_rows:
            created_items = self._insert_rows(db, valid_rows)

        total_count = len(payload.items)
        success_count = len(created_items)
        failure_count = total_count - success_count

        return PartnerBulkCreateResult(
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            created_items=created_items,
            errors=sorted(errors, key=lambda x: x.row_number),
        )

    def _normalize_and_validate(
        self,
        items,
    ) -> tuple[list[_NormalizedPartnerRow], list[PartnerBulkError]]:
        rows: list[_NormalizedPartnerRow] = []
        errors: list[PartnerBulkError] = []

        for item in items:
            name = item.name.strip()
            business_no = item.business_no.strip().replace("-", "")
            partner_type = item.partner_type.value.strip().upper()

            if not name:
                errors.append(
                    PartnerBulkError(
                        row_number=item.row_number,
                        field="name",
                        message="name is required",
                    )
                )

            if not business_no:
                errors.append(
                    PartnerBulkError(
                        row_number=item.row_number,
                        field="business_no",
                        message="business_no is required",
                    )
                )

            if partner_type not in {"CUSTOMER", "VENDOR"}:
                errors.append(
                    PartnerBulkError(
                        row_number=item.row_number,
                        field="partner_type",
                        message="partner_type must be CUSTOMER or VENDOR",
                    )
                )

            rows.append(
                _NormalizedPartnerRow(
                    row_number=item.row_number,
                    partner_type=partner_type,
                    name=name,
                    business_no=business_no,
                    is_active=item.is_active,
                )
            )

        return rows, errors

    def _validate_duplicate_business_no_in_payload(
        self,
        rows: Iterable[_NormalizedPartnerRow],
    ) -> list[PartnerBulkError]:
        errors: list[PartnerBulkError] = []
        seen: dict[str, int] = {}

        for row in rows:
            first_row = seen.get(row.business_no)
            if first_row is None:
                seen[row.business_no] = row.row_number
                continue

            errors.append(
                PartnerBulkError(
                    row_number=row.row_number,
                    field="business_no",
                    message=f"duplicated in payload (first row: {first_row})",
                )
            )

        return errors

    def _validate_duplicate_business_no_in_db(
        self,
        db: Session,
        rows: Iterable[_NormalizedPartnerRow],
    ) -> list[PartnerBulkError]:
        errors: list[PartnerBulkError] = []
        business_nos = list({row.business_no for row in rows})

        if not business_nos:
            return errors

        existing_business_nos = {
            value
            for (value,) in db.query(Partner.business_no)
            .filter(Partner.business_no.in_(business_nos))
            .all()
        }

        for row in rows:
            if row.business_no in existing_business_nos:
                errors.append(
                    PartnerBulkError(
                        row_number=row.row_number,
                        field="business_no",
                        message="business_no already exists",
                    )
                )

        return errors

    def _exclude_error_rows(
        self,
        rows: Iterable[_NormalizedPartnerRow],
        errors: Iterable[PartnerBulkError],
    ) -> list[_NormalizedPartnerRow]:
        error_row_numbers = {error.row_number for error in errors}
        return [row for row in rows if row.row_number not in error_row_numbers]

    def _insert_rows(
        self,
        db: Session,
        rows: Iterable[_NormalizedPartnerRow],
    ) -> list[Partner]:
        objects = [
            Partner(
                partner_type=row.partner_type,
                name=row.name,
                business_no=row.business_no,
                is_active=row.is_active,
            )
            for row in rows
        ]

        try:
            db.add_all(objects)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise
        for obj in objects:
            db.refresh(obj)

        return objects


partner_bulk_service = PartnerBulkService()