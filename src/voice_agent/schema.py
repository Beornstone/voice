from typing import Literal
from pydantic import BaseModel, Field


PAYEES_ALLOWED = ["James (Son)", "Pete (Doctor)", "Sarah (Landlord)", "Aisha (Friend)"]


class CheckBalanceIntent(BaseModel):
    intent: Literal["CHECK_BALANCE"]
    assistant_say: str


class TransferDraftIntent(BaseModel):
    intent: Literal["TRANSFER_DRAFT"]
    payee_label: str
    amount: float
    currency: Literal["EUR"] = "EUR"
    assistant_say: str


class ConfirmIntent(BaseModel):
    intent: Literal["CONFIRM"]
    assistant_say: str


class CancelIntent(BaseModel):
    intent: Literal["CANCEL"]
    assistant_say: str


class ClarifyIntent(BaseModel):
    intent: Literal["CLARIFY"]
    assistant_say: str
    choices: list[str] | None = None


class HelpIntent(BaseModel):
    intent: Literal["HELP"]
    assistant_say: str


Intent = CheckBalanceIntent | TransferDraftIntent | ConfirmIntent | CancelIntent | ClarifyIntent | HelpIntent


class GoHomeAction(BaseModel):
    type: Literal["GO_HOME"]


class OpenBalanceAction(BaseModel):
    type: Literal["OPEN_BALANCE"]


class OpenTransferAction(BaseModel):
    type: Literal["OPEN_TRANSFER"]
    payee_label: str
    amount: float
    currency: Literal["EUR"] = "EUR"


class HighlightSendAction(BaseModel):
    type: Literal["HIGHLIGHT_SEND"]


UIAction = GoHomeAction | OpenBalanceAction | OpenTransferAction | HighlightSendAction


class TurnRequest(BaseModel):
    session_id: str
    transcript: str = Field(min_length=1)


class TurnResponse(BaseModel):
    assistant_say: str
    intent: Intent
    ui_action: UIAction | None = None
    debug: dict | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
