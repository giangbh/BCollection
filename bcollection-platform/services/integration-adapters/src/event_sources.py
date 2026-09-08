"""Versioned REST event contracts. No source-provided case/PTP allocation is trusted."""
from datetime import datetime, timezone
import os
from typing import Literal
from urllib.parse import quote, urlencode
from pydantic import BaseModel, Field, field_validator, model_validator
from rest_transport import RestTransport, AdapterError


class Timed(BaseModel):
    occurred_at: datetime

    @field_validator('occurred_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError('Timezone-aware non-future event required')
        return value


class PaymentEvent(Timed):
    event_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(strict=True, ge=1)
    loan_id: str = Field(min_length=1)
    debtor_cif: str = Field(min_length=1)
    kind: Literal['POSTED', 'REVERSED']
    amount_vnd: int = Field(strict=True, gt=0)
    reverses_event_id: str | None = None

    @model_validator(mode='after')
    def reversal(self):
        if (self.kind == 'REVERSED') != bool(self.reverses_event_id):
            raise ValueError('Invalid reversal reference')
        return self


class SignalEvent(Timed):
    event_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(strict=True, ge=1)
    signal_id: str = Field(min_length=1, max_length=128)
    signal_version: int = Field(strict=True, ge=1)
    debtor_cif: str = Field(min_length=1)
    loan_ids: list[str] = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=500)
    severity: Literal['HIGH', 'MEDIUM', 'LOW']
    verification: Literal['VERIFIED', 'UNVERIFIED', 'DISMISSED']

    @field_validator('loan_ids')
    @classmethod
    def unique_loans(cls, value):
        if len(value) != len(set(value)) or any(not s.strip() for s in value):
            raise ValueError('Unique non-empty loans required')
        return value


class Page(BaseModel):
    contract_version: Literal['1.0']
    data_origin: Literal['SYNTHETIC']
    source_system: Literal['MOCK_CORE', 'MOCK_EWS']
    stream_id: str
    debtor_cif: str = Field(min_length=1)
    after_cursor: int = Field(strict=True, ge=0)
    next_cursor: int = Field(strict=True, ge=0)
    has_more: bool = Field(strict=True)
    complete_through: datetime | None
    events: list[dict] = Field(max_length=100)

    @field_validator('complete_through')
    @classmethod
    def watermark(cls, value):
        if value and (value.tzinfo is None or value > datetime.now(timezone.utc)):
            raise ValueError('Invalid completeness watermark')
        return value


class EventSourceAdapter:
    def fetch(self, kind, stream, cursor):
        env, source = ('CORE_BANKING_API_URL', 'MOCK_CORE') if kind == 'payment' else ('EWS_API_URL', 'MOCK_EWS')
        route = f'loans/{quote(stream, safe="")}/payment-events' if kind == 'payment' else f'customers/{quote(stream, safe="")}/signals'
        raw = RestTransport(os.environ[env]).get(route + '?' + urlencode({'cursor': cursor, 'limit': 100}))
        try:
            page = Page.model_validate(raw)
            model = PaymentEvent if kind == 'payment' else SignalEvent
            events = [model.model_validate(e).model_dump(mode='json') for e in page.events]
            if page.source_system != source or page.stream_id != stream or page.after_cursor != cursor:
                raise ValueError('Stream mismatch')
            if [e['sequence'] for e in events] != list(range(cursor + 1, cursor + len(events) + 1)):
                raise ValueError('Sequence gap')
            if page.next_cursor != cursor + len(events) or (page.has_more and not events):
                raise ValueError('Invalid cursor')
            if len({e['event_id'] for e in events}) != len(events):
                raise ValueError('Duplicate event ID')
            if any(e['loan_id' if kind == 'payment' else 'debtor_cif'] != stream for e in events):
                raise ValueError('Item identity mismatch')
            if any(e['debtor_cif'] != page.debtor_cif for e in events) or (kind == 'ews' and page.debtor_cif != stream):
                raise ValueError('Stream debtor mismatch')
            result = page.model_dump(mode='json')
            result['events'] = events
            return result
        except (ValueError, KeyError, TypeError):
            raise AdapterError('INVALID_EVENT_CONTRACT') from None


class OutcomePublisherAdapter:
    def send(self, event):
        result = RestTransport(os.environ['EWS_API_URL']).post('collection-outcomes', event, event['event_id'])
        if result.get('event_id') != event['event_id'] or result.get('accepted') is not True or not result.get('receipt_id'):
            raise AdapterError('INVALID_ACK')
        return result
