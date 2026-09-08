"""ADP-02 read ports and validated canonical contracts, independent of persistence."""
import os
from datetime import datetime
from typing import Literal
from urllib.parse import quote
from pydantic import BaseModel, Field, field_validator
from core_banking.contracts import CoreSnapshot, Money
from rest_transport import RestTransport, AdapterError


class Profile(BaseModel):
    debtor_cif: str = Field(min_length=1)
    party_type: Literal['INDIVIDUAL', 'ORGANIZATION']
    legal_name: str = Field(min_length=1)
    tax_id: str | None
    industry: str | None
    region: str | None
    rm_user_id: str | None


class Instalment(BaseModel):
    due_at: datetime
    amount_vnd: Money

    @field_validator('due_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timezone required')
        return value


class Loan(CoreSnapshot):
    product_code: str = Field(min_length=1)
    repayment_schedule: list[Instalment]


class History(BaseModel):
    debtor_cif: str = Field(min_length=1)
    loan_id: str = Field(min_length=1)
    observed_at: datetime
    dpd: int = Field(strict=True, ge=0)

    @field_validator('observed_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timezone required')
        return value


class Collateral(BaseModel):
    debtor_cif: str = Field(min_length=1)
    collateral_id: str = Field(min_length=1)
    loan_ids: list[str] = Field(min_length=1)
    description: str = Field(min_length=1)
    valuation_vnd: Money
    valued_at: datetime
    legal_status: Literal['PLEDGED', 'RELEASED', 'UNKNOWN']

    @field_validator('valued_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timezone required')
        return value


class Staff(BaseModel):
    user_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    org_unit: str = Field(min_length=1)


class Envelope(BaseModel):
    contract_version: Literal['1.0']
    debtor_cif: str = Field(min_length=1)
    source_system: str = Field(min_length=1)
    source_version: int = Field(strict=True, ge=1)
    as_of: datetime
    data_origin: Literal['SYNTHETIC', 'EXTERNAL']
    coverage: Literal['COMPLETE', 'PARTIAL']
    items: list[dict] = Field(max_length=5000)

    @field_validator('as_of')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Timezone required')
        return value


MODELS = {'profile': Profile, 'loans': Loan, 'history': History,
          'collateral': Collateral, 'directory': Staff}
KEYS = {'profile': lambda x: x['debtor_cif'], 'loans': lambda x: x['loan_id'],
        'history': lambda x: (x['loan_id'], x['observed_at']),
        'collateral': lambda x: x['collateral_id'], 'directory': lambda x: x['user_id']}


def validate_resource(raw, kind, cif, now, origin):
    try:
        envelope = Envelope.model_validate(raw)
        if envelope.debtor_cif != cif or envelope.data_origin != origin:
            raise ValueError('Identity/origin mismatch')
        if (envelope.as_of - now).total_seconds() > 30:
            raise ValueError('Future source timestamp')
        items = [MODELS[kind].model_validate(item).model_dump(mode='json') for item in envelope.items]
        if kind == 'profile' and len(items) != 1:
            raise ValueError('Exactly one customer profile required')
        if any(item.get('debtor_cif', cif) != cif for item in items):
            raise ValueError('Item identity mismatch')
        keys = [KEYS[kind](item) for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate source item')
        time_key = {'history': 'observed_at', 'collateral': 'valued_at', 'loans': 'as_of'}.get(kind)
        if time_key and any(datetime.fromisoformat(item[time_key]) > envelope.as_of for item in items):
            raise ValueError('Observation exceeds source watermark')
        result = envelope.model_dump(mode='json')
        result['items'] = items
        return result
    except (ValueError, KeyError, TypeError):
        raise AdapterError('INVALID_CONTRACT') from None


class CustomerMasterAdapter:
    def fetch(self, cif):
        return RestTransport(os.environ['CRM_API_URL'], os.getenv('CRM_API_KEY', '')).get(f'customers/{quote(cif, safe="")}/profile')


class CoreCustomerAdapter:
    def fetch(self, cif, resource):
        if resource not in {'loans', 'history'}:
            raise ValueError('Unknown Core resource')
        return RestTransport(os.environ['CORE_BANKING_API_URL'], os.getenv('CORE_BANKING_API_KEY', '')).get(f'customers/{quote(cif, safe="")}/{resource}')


class CollateralAdapter:
    def fetch(self, cif):
        return RestTransport(os.environ['LOS_API_URL'], os.getenv('LOS_API_KEY', '')).get(f'customers/{quote(cif, safe="")}/collaterals')


class DirectoryAdapter:
    def fetch(self, cif):
        # Staff associated with this customer; never a logged-in identity or case assignment.
        return RestTransport(os.environ['DIRECTORY_API_URL'], os.getenv('DIRECTORY_API_KEY', '')).get(f'customers/{quote(cif, safe="")}/staff')
