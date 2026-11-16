"""Pydantic request schemas matching docs/CONTRACT.md A6."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Complaint = Literal["chest_pain", "shortness_of_breath", "stroke_signs", "abdominal_pain", "trauma",
                    "altered_mental_status", "fever_infection", "other"]
Injury = Literal["minor_wound", "suspected_fracture", "open_fracture", "minor_burn", "major_burn",
                 "heavy_bleeding", "frostbite"]
BedType = Literal["icu_review", "telemetry", "isolation", "floor"]


class Vitals(BaseModel):
    time: Optional[str] = None  # ISO-8601; server fills "now" if missing
    source: Literal["ambulance", "triage", "er"] = "er"
    resp_rate: Optional[float] = Field(None, ge=0, le=80)
    spo2: Optional[float] = Field(None, ge=0, le=100)
    on_oxygen: Optional[bool] = None
    sbp: Optional[float] = Field(None, ge=0, le=300)
    dbp: Optional[float] = Field(None, ge=0, le=250)
    heart_rate: Optional[float] = Field(None, ge=0, le=300)
    temp_c: Optional[float] = Field(None, ge=25, le=45)
    avpu: Optional[Literal["A", "C", "V", "P", "U"]] = None  # C = new confusion
    gcs: Optional[int] = Field(None, ge=3, le=15)
    pain: Optional[int] = Field(None, ge=0, le=10)
    glucose_mg_dl: Optional[float] = Field(None, ge=0, le=2000)
    rhythm: Optional[str] = None


class Treatment(BaseModel):
    time: Optional[str] = None
    what: str


class PatientCreate(BaseModel):
    name: str
    age: int = Field(ge=0, le=120)
    sex: Literal["M", "F"]
    complaint_category: Complaint
    complaint_text: str = ""
    onset_time: Optional[str] = None
    history: str = ""
    medications: str = ""
    allergies: str = ""
    injuries: List[Injury] = []
    treatments: List[Treatment] = []
    vitals: Optional[Vitals] = None  # first ambulance set
    demo: bool = False


class TriageIn(BaseModel):
    esi: int = Field(ge=1, le=5)
    vitals: Optional[Vitals] = None


class EcgIn(BaseModel):
    record_id: str


class XrayIn(BaseModel):
    image_id: str


class ReviewIn(BaseModel):
    type: Literal["ecg", "xray"]
    normal: bool
    by: str


class BedRequestIn(BaseModel):
    bed_type: BedType
    confirmed_by: str
