from pydantic import BaseModel


class RecordOpportunityViewRequest(BaseModel):
    opportunity_id: str
