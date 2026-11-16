# API examples (generated from the running backend)

Base URL: `http://localhost:8000`. CORS is open. Times are UTC ISO-8601.

### GET `/board`

Response (200) — first entry of the list:
```json
[
  {
    "patient": {
      "id": "P-003",
      "demo": true,
      "name": "Demo Patient C (fictional)",
      "age": 81,
      "sex": "M",
      "complaint_category": "shortness_of_breath",
      "complaint_text": "Short of breath for 2 days, productive cough",
      "onset_time": "2026-11-14T01:54:58+00:00",
      "history": "COPD, atrial fibrillation",
      "medications": "Tiotropium, apixaban",
      "allergies": "None known",
      "injuries": [],
      "treatments": [
        {
          "time": "2026-11-16T01:04:58+00:00",
          "what": "Albuterol nebulizer"
        }
      ],
      "vitals": [
        {
          "source": "ambulance",
          "resp_rate": 22,
          "spo2": 93,
          "on_oxygen": false,
          "sbp": 124,
          "dbp": 70,
          "heart_rate": 98,
          "temp_c": 38.6,
          "avpu": "A",
          "gcs": 15,
          "pain": 2,
          "time": "2026-11-16T01:04:58+00:00"
        }
      ],
      "esi": 2,
      "status": "waiting",
      "arrival_time": "2026-11-16T01:09:58+00:00",
      "ecg": null,
      "xray": {
        "image_id": "00000773_001.png",
        "result": {
          "findings": {
            "Pneumonia": 0.74,
            "Effusion": 0.05,
            "Edema": 0.05,
            "Cardiomegaly": 0.05,
            "Pneumothorax": 0.05
          },
          "flagged": [
            "Pneumonia"
          ],
          "thresholds": {
            "Pneumonia": 0.5,
            "Effusion": 0.5,
            "Edema": 0.5,
            "Cardiomegaly": 0.5,
            "Pneumothorax": 0.5
          },
          "model": "stub",
          "note": "AI flag, not a diagnosis"
        },
        "time": "2026-11-16T01:39:58+00:00"
      },
      "reviews": [],
      "bed_request": null,
      "created_time": "2026-11-16T01:54:58+00:00"
    },
    "scores": {
      "admission": {
        "probability": 0.95,
        "stage": "triage",
        "model": "stub",
        "top_reasons": [
          {
            "label": "Age 81",
            "direction": "up"
          },
          {
            "label": "SpO2 93%",
            "direction": "up"
          }
        ]
      },
      "news2": {
        "value": 6,
        "band": "medium",
        "complete": true,
        "present": 7,
        "parts": {
          "resp_rate": 2,
          "spo2": 2,
          "on_oxygen": 0,
          "sbp": 0,
          "heart_rate": 1,
          "temp_c": 1,
          "consciousness": 0
        },
        "trend": null,
        "previous": null
      },
      "findings": {
        "points": 10,
        "items": [
          {
            "source": "xray",
            "points": 10,
            "label": "X-ray flags Pneumonia (AI, unreviewed)"
          }
        ]
      },
      "parts": {
        "A": 95,
        "B": 30,
        "C": 10
      },
      "priority": 72,
      "wait_minutes": 45,
      "queue_rank_score": 75
    },
    "bed_type": {
      "suggested": "isolation",
      "reason": "X-ray flags pneumonia (AI) and temperature 38.6 °C"
    },
    "alerts": [],
    "pending": [
      "ECG not yet recorded",
      "X-ray AI flag awaiting clinician review",
      "Bed request not sent"
    ],
    "handoff": {
      "mist": "M — Mechanism/complaint: shortness of breath: Short of breath for 2 days, productive cough. Onset 17:54.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 98, BP 124/70, RR 22, SpO2 93% (room air), temp 38.6 °C, consciousness A, pain 2/10. NEWS2 6.\nT — Treatment: 17:04 Albuterol nebulizer.",
      "sbar": "S — 81-year-old man, shortness of breath. Suggested bed: Possible isolation (X-ray flags pneumonia (AI) and temperature 38.6 °C).\nB — History: COPD, atrial fibrillation. Medications: Tiotropium, apixaban. Allergies: None known. ESI: 2.\nA — Latest vitals: HR 98, BP 124/70, RR 22, SpO2 93% (room air), temp 38.6 °C, consciousness A, pain 2/10. NEWS2 6 (medium). Admission likelihood 95% (model stub). ECG: not yet done. X-ray: AI flags Pneumonia, not yet reviewed by a clinician (model stub; AI flag, not a diagnosis).\nR — Items to check: ECG not yet recorded; X-ray AI flag awaiting clinician review; Bed request not sent."
    }
  }
]
```

### POST `/patients`

Body:
```json
{
  "name": "Demo Patient G (fictional)",
  "age": 62,
  "sex": "M",
  "complaint_category": "chest_pain",
  "complaint_text": "Chest tightness 30 min",
  "history": "HTN",
  "medications": "lisinopril",
  "allergies": "none known",
  "injuries": [],
  "treatments": [
    {
      "what": "Aspirin 324 mg PO"
    }
  ],
  "vitals": {
    "resp_rate": 18,
    "spo2": 96,
    "on_oxygen": false,
    "sbp": 142,
    "dbp": 88,
    "heart_rate": 96,
    "temp_c": 36.8,
    "avpu": "A",
    "pain": 6
  }
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-008",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": null,
    "arrival_time": null,
    "status": "en_route",
    "ecg": null,
    "xray": null,
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.39,
      "stage": "ambulance",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 1,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 0,
        "spo2": 0,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": null,
      "previous": null
    },
    "findings": {
      "points": 0,
      "items": []
    },
    "parts": {
      "A": 39,
      "B": 5,
      "C": 0
    },
    "priority": 22,
    "wait_minutes": null,
    "queue_rank_score": null
  },
  "bed_type": {
    "suggested": "floor",
    "reason": "No other rule matched"
  },
  "alerts": [
    {
      "kind": "protocol",
      "level": "warning",
      "message": "Chest pain: ECG due within 10 min of arrival",
      "due_at": null
    }
  ],
  "pending": [
    "Patient en route",
    "ECG not yet recorded",
    "X-ray read pending"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 1.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Regular floor (No other rule matched).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: not recorded.\nA — Latest vitals: HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 1 (low). Admission likelihood 39% (model stub). ECG: not yet done. X-ray: not yet done.\nR — Items to check: Chest pain: ECG due within 10 min of arrival; Patient en route; ECG not yet recorded; X-ray read pending."
  }
}
```

### POST `/patients/P-007/arrive`

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": null,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": null,
    "xray": null,
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.39,
      "stage": "ambulance",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 1,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 0,
        "spo2": 0,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": null,
      "previous": null
    },
    "findings": {
      "points": 0,
      "items": []
    },
    "parts": {
      "A": 39,
      "B": 5,
      "C": 0
    },
    "priority": 22,
    "wait_minutes": 0,
    "queue_rank_score": 22
  },
  "bed_type": {
    "suggested": "floor",
    "reason": "No other rule matched"
  },
  "alerts": [
    {
      "kind": "protocol",
      "level": "warning",
      "message": "ECG due within 10 min of arrival",
      "due_at": "2026-11-16T02:04:58+00:00"
    }
  ],
  "pending": [
    "ESI not yet assigned",
    "ECG not yet recorded",
    "X-ray read pending",
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 1.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Regular floor (No other rule matched).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: not recorded.\nA — Latest vitals: HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 1 (low). Admission likelihood 39% (model stub). ECG: not yet done. X-ray: not yet done.\nR — Items to check: ECG due within 10 min of arrival; ESI not yet assigned; ECG not yet recorded; X-ray read pending; Bed request not sent."
  }
}
```

### POST `/patients/P-007/vitals`

Body:
```json
{
  "heart_rate": 104,
  "resp_rate": 22,
  "spo2": 95,
  "on_oxygen": false,
  "sbp": 136,
  "temp_c": 37.0,
  "avpu": "A",
  "source": "er"
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": null,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": null,
    "xray": null,
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.39,
      "stage": "ambulance",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 0,
      "items": []
    },
    "parts": {
      "A": 39,
      "B": 20,
      "C": 0
    },
    "priority": 30,
    "wait_minutes": 0,
    "queue_rank_score": 30
  },
  "bed_type": {
    "suggested": "floor",
    "reason": "No other rule matched"
  },
  "alerts": [
    {
      "kind": "protocol",
      "level": "warning",
      "message": "ECG due within 10 min of arrival",
      "due_at": "2026-11-16T02:04:58+00:00"
    },
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [
    "ESI not yet assigned",
    "ECG not yet recorded",
    "X-ray read pending",
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Regular floor (No other rule matched).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: not recorded.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 39% (model stub). ECG: not yet done. X-ray: not yet done.\nR — Items to check: ECG due within 10 min of arrival; NEWS2 rose from 1 to 4; ESI not yet assigned; ECG not yet recorded; X-ray read pending; Bed request not sent."
  }
}
```

### POST `/patients/P-007/triage`

Body:
```json
{
  "esi": 2
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": null,
    "xray": null,
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 0,
      "items": []
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 0
    },
    "priority": 37,
    "wait_minutes": 0,
    "queue_rank_score": 37
  },
  "bed_type": {
    "suggested": "floor",
    "reason": "No other rule matched"
  },
  "alerts": [
    {
      "kind": "protocol",
      "level": "warning",
      "message": "ECG due within 10 min of arrival",
      "due_at": "2026-11-16T02:04:58+00:00"
    },
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [
    "ECG not yet recorded",
    "X-ray read pending",
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Regular floor (No other rule matched).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: not yet done. X-ray: not yet done.\nR — Items to check: ECG due within 10 min of arrival; NEWS2 rose from 1 to 4; ECG not yet recorded; X-ray read pending; Bed request not sent."
  }
}
```

### POST `/patients/P-007/ecg`

Body:
```json
{
  "record_id": "ptbxl_14912"
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": {
      "record_id": "ptbxl_14912",
      "result": {
        "abnormal_prob": 0.86,
        "abnormal": true,
        "threshold": 0.5,
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "xray": null,
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 10,
      "items": [
        {
          "source": "ecg",
          "points": 10,
          "label": "Abnormal ECG (AI, unreviewed)"
        }
      ]
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 10
    },
    "priority": 47,
    "wait_minutes": 0,
    "queue_rank_score": 47
  },
  "bed_type": {
    "suggested": "telemetry",
    "reason": "Abnormal ECG (AI flag, unreviewed)"
  },
  "alerts": [
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [
    "X-ray read pending",
    "ECG AI flag awaiting clinician review",
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Telemetry (heart-monitored) (Abnormal ECG (AI flag, unreviewed)).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: AI flag abnormal (p=0.86), not yet reviewed by a clinician (model stub; AI flag, not a diagnosis). X-ray: not yet done.\nR — Items to check: NEWS2 rose from 1 to 4; X-ray read pending; ECG AI flag awaiting clinician review; Bed request not sent."
  }
}
```

### POST `/patients/P-007/xray`

Body:
```json
{
  "image_id": "00000842_000.png"
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": {
      "record_id": "ptbxl_14912",
      "result": {
        "abnormal_prob": 0.86,
        "abnormal": true,
        "threshold": 0.5,
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "xray": {
      "image_id": "00000842_000.png",
      "result": {
        "findings": {
          "Pneumonia": 0.05,
          "Effusion": 0.05,
          "Edema": 0.05,
          "Cardiomegaly": 0.05,
          "Pneumothorax": 0.05
        },
        "flagged": [],
        "thresholds": {
          "Pneumonia": 0.5,
          "Effusion": 0.5,
          "Edema": 0.5,
          "Cardiomegaly": 0.5,
          "Pneumothorax": 0.5
        },
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "reviews": [],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 10,
      "items": [
        {
          "source": "ecg",
          "points": 10,
          "label": "Abnormal ECG (AI, unreviewed)"
        }
      ]
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 10
    },
    "priority": 47,
    "wait_minutes": 0,
    "queue_rank_score": 47
  },
  "bed_type": {
    "suggested": "telemetry",
    "reason": "Abnormal ECG (AI flag, unreviewed)"
  },
  "alerts": [
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [
    "ECG AI flag awaiting clinician review",
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Telemetry (heart-monitored) (Abnormal ECG (AI flag, unreviewed)).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: AI flag abnormal (p=0.86), not yet reviewed by a clinician (model stub; AI flag, not a diagnosis). X-ray: no AI flag (model stub; AI flag, not a diagnosis).\nR — Items to check: NEWS2 rose from 1 to 4; ECG AI flag awaiting clinician review; Bed request not sent."
  }
}
```

### POST `/patients/P-007/review`

Body:
```json
{
  "type": "ecg",
  "normal": false,
  "by": "MD Demo"
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "waiting",
    "ecg": {
      "record_id": "ptbxl_14912",
      "result": {
        "abnormal_prob": 0.86,
        "abnormal": true,
        "threshold": 0.5,
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "xray": {
      "image_id": "00000842_000.png",
      "result": {
        "findings": {
          "Pneumonia": 0.05,
          "Effusion": 0.05,
          "Edema": 0.05,
          "Cardiomegaly": 0.05,
          "Pneumothorax": 0.05
        },
        "flagged": [],
        "thresholds": {
          "Pneumonia": 0.5,
          "Effusion": 0.5,
          "Edema": 0.5,
          "Cardiomegaly": 0.5,
          "Pneumothorax": 0.5
        },
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "reviews": [
      {
        "type": "ecg",
        "normal": false,
        "by": "MD Demo",
        "time": "2026-11-16T01:54:58+00:00"
      }
    ],
    "bed_request": null,
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 10,
      "items": [
        {
          "source": "ecg",
          "points": 10,
          "label": "Abnormal ECG (AI, confirmed by clinician)"
        }
      ]
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 10
    },
    "priority": 47,
    "wait_minutes": 0,
    "queue_rank_score": 47
  },
  "bed_type": {
    "suggested": "telemetry",
    "reason": "Abnormal ECG (AI flag, confirmed)"
  },
  "alerts": [
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [
    "Bed request not sent"
  ],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Telemetry (heart-monitored) (Abnormal ECG (AI flag, confirmed)).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: AI flag abnormal (p=0.86), confirmed by clinician (model stub; AI flag, not a diagnosis). X-ray: no AI flag (model stub; AI flag, not a diagnosis).\nR — Items to check: NEWS2 rose from 1 to 4; Bed request not sent."
  }
}
```

### POST `/patients/P-007/bed-request`

Body:
```json
{
  "bed_type": "telemetry",
  "confirmed_by": "Charge RN Demo"
}
```

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "bed_requested",
    "ecg": {
      "record_id": "ptbxl_14912",
      "result": {
        "abnormal_prob": 0.86,
        "abnormal": true,
        "threshold": 0.5,
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "xray": {
      "image_id": "00000842_000.png",
      "result": {
        "findings": {
          "Pneumonia": 0.05,
          "Effusion": 0.05,
          "Edema": 0.05,
          "Cardiomegaly": 0.05,
          "Pneumothorax": 0.05
        },
        "flagged": [],
        "thresholds": {
          "Pneumonia": 0.5,
          "Effusion": 0.5,
          "Edema": 0.5,
          "Cardiomegaly": 0.5,
          "Pneumothorax": 0.5
        },
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "reviews": [
      {
        "type": "ecg",
        "normal": false,
        "by": "MD Demo",
        "time": "2026-11-16T01:54:58+00:00"
      }
    ],
    "bed_request": {
      "bed_type": "telemetry",
      "confirmed_by": "Charge RN Demo",
      "time": "2026-11-16T01:54:58+00:00"
    },
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 10,
      "items": [
        {
          "source": "ecg",
          "points": 10,
          "label": "Abnormal ECG (AI, confirmed by clinician)"
        }
      ]
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 10
    },
    "priority": 47,
    "wait_minutes": 0,
    "queue_rank_score": 47
  },
  "bed_type": {
    "suggested": "telemetry",
    "reason": "Abnormal ECG (AI flag, confirmed)"
  },
  "alerts": [
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Telemetry (heart-monitored) (Abnormal ECG (AI flag, confirmed)).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: AI flag abnormal (p=0.86), confirmed by clinician (model stub; AI flag, not a diagnosis). X-ray: no AI flag (model stub; AI flag, not a diagnosis).\nR — Items to check: NEWS2 rose from 1 to 4."
  }
}
```

### GET `/patients/P-007`

Response (200):
```json
{
  "patient": {
    "id": "P-007",
    "demo": false,
    "name": "Demo Patient G (fictional)",
    "age": 62,
    "sex": "M",
    "complaint_category": "chest_pain",
    "complaint_text": "Chest tightness 30 min",
    "onset_time": null,
    "history": "HTN",
    "medications": "lisinopril",
    "allergies": "none known",
    "injuries": [],
    "treatments": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "what": "Aspirin 324 mg PO"
      }
    ],
    "vitals": [
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "ambulance",
        "resp_rate": 18.0,
        "spo2": 96.0,
        "on_oxygen": false,
        "sbp": 142.0,
        "dbp": 88.0,
        "heart_rate": 96.0,
        "temp_c": 36.8,
        "avpu": "A",
        "gcs": null,
        "pain": 6,
        "glucose_mg_dl": null,
        "rhythm": null
      },
      {
        "time": "2026-11-16T01:54:58+00:00",
        "source": "er",
        "resp_rate": 22.0,
        "spo2": 95.0,
        "on_oxygen": false,
        "sbp": 136.0,
        "dbp": null,
        "heart_rate": 104.0,
        "temp_c": 37.0,
        "avpu": "A",
        "gcs": null,
        "pain": null,
        "glucose_mg_dl": null,
        "rhythm": null
      }
    ],
    "esi": 2,
    "arrival_time": "2026-11-16T01:54:58+00:00",
    "status": "bed_requested",
    "ecg": {
      "record_id": "ptbxl_14912",
      "result": {
        "abnormal_prob": 0.86,
        "abnormal": true,
        "threshold": 0.5,
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "xray": {
      "image_id": "00000842_000.png",
      "result": {
        "findings": {
          "Pneumonia": 0.05,
          "Effusion": 0.05,
          "Edema": 0.05,
          "Cardiomegaly": 0.05,
          "Pneumothorax": 0.05
        },
        "flagged": [],
        "thresholds": {
          "Pneumonia": 0.5,
          "Effusion": 0.5,
          "Edema": 0.5,
          "Cardiomegaly": 0.5,
          "Pneumothorax": 0.5
        },
        "model": "stub",
        "note": "AI flag, not a diagnosis"
      },
      "time": "2026-11-16T01:54:58+00:00"
    },
    "reviews": [
      {
        "type": "ecg",
        "normal": false,
        "by": "MD Demo",
        "time": "2026-11-16T01:54:58+00:00"
      }
    ],
    "bed_request": {
      "bed_type": "telemetry",
      "confirmed_by": "Charge RN Demo",
      "time": "2026-11-16T01:54:58+00:00"
    },
    "created_time": "2026-11-16T01:54:58+00:00"
  },
  "scores": {
    "admission": {
      "probability": 0.54,
      "stage": "triage",
      "model": "stub",
      "top_reasons": [
        {
          "label": "Age 62",
          "direction": "up"
        }
      ]
    },
    "news2": {
      "value": 4,
      "band": "low",
      "complete": true,
      "present": 7,
      "parts": {
        "resp_rate": 2,
        "spo2": 1,
        "on_oxygen": 0,
        "sbp": 0,
        "heart_rate": 1,
        "temp_c": 0,
        "consciousness": 0
      },
      "trend": "up",
      "previous": 1
    },
    "findings": {
      "points": 10,
      "items": [
        {
          "source": "ecg",
          "points": 10,
          "label": "Abnormal ECG (AI, confirmed by clinician)"
        }
      ]
    },
    "parts": {
      "A": 54,
      "B": 20,
      "C": 10
    },
    "priority": 47,
    "wait_minutes": 0,
    "queue_rank_score": 47
  },
  "bed_type": {
    "suggested": "telemetry",
    "reason": "Abnormal ECG (AI flag, confirmed)"
  },
  "alerts": [
    {
      "kind": "deterioration",
      "level": "warning",
      "message": "NEWS2 rose from 1 to 4",
      "due_at": null
    }
  ],
  "pending": [],
  "handoff": {
    "mist": "M — Mechanism/complaint: chest pain: Chest tightness 30 min. Onset not recorded.\nI — Injuries: none recorded.\nS — Signs (latest ambulance set): HR 96, BP 142/88, RR 18, SpO2 96% (room air), temp 36.8 °C, consciousness A, pain 6/10. NEWS2 4.\nT — Treatment: 17:54 Aspirin 324 mg PO.",
    "sbar": "S — 62-year-old man, chest pain. Suggested bed: Telemetry (heart-monitored) (Abnormal ECG (AI flag, confirmed)).\nB — History: HTN. Medications: lisinopril. Allergies: none known. ESI: 2.\nA — Latest vitals: HR 104, BP 136, RR 22, SpO2 95% (room air), temp 37 °C, consciousness A, pain not recorded. NEWS2 4 (low), trend up from 1. Admission likelihood 54% (model stub). ECG: AI flag abnormal (p=0.86), confirmed by clinician (model stub; AI flag, not a diagnosis). X-ray: no AI flag (model stub; AI flag, not a diagnosis).\nR — Items to check: NEWS2 rose from 1 to 4."
  }
}
```

### GET `/rules`

Response (200):
```json
{
  "text": "HOW THE BED-PRIORITY SCORE WORKS\n\nA. Needs a bed (0-100): admission probability from a model trained on the Yale ED admission dataset, x 100. The \"ambulance\" model (no ESI) is used until a triage nurse enters ESI, then the \"triage\" model.\n\nB. Sick right now (0-100): NEWS2 (0-20) x 5, from the latest complete set of vital signs. NEWS2 uses breathing rate, oxygen saturation (Scale 1 only), air or oxygen, systolic blood pressure, pulse, consciousness and temperature. If a parameter is missing, NEWS2 is shown as incomplete (n/7) and counts only the parameters present.\n\nC. Findings (points added):\n- ECG AI flag (abnormal): +10\n- Chest X-ray AI flag (any of pneumonia, effusion, edema, cardiomegaly, pneumothorax): +10\n- Visible injuries: minor wound 2, suspected fracture 5, open fracture 10, minor burn 5, major burn 15, heavy bleeding 15, frostbite 5. DRAFT: clinician review needed.\n\nBed priority = min(100, round((A + B) / 2 + C)).\n\nAI can only raise the score. A normal AI result adds 0 and never removes an earlier flag. Only a clinician marking a finding \"Reviewed - normal\" removes its points.\n\nQueue rank = bed priority + 1 point per full 15 minutes waited since arrival, so nobody waits forever.\n\nSuggested bed type (DRAFT rules, first match wins):\n1. NEWS2 7 or more, or GCS 8 or less -> ICU review\n2. Abnormal ECG AI flag (unreviewed or confirmed) -> Telemetry (heart-monitored)\n3. X-ray AI flags pneumonia and temperature 38.1 C or more -> Possible isolation\n4. Otherwise -> Regular floor\nThe charge nurse confirms every bed request. The app never assigns a bed.\n\nProtocol alerts (not driven by the score):\n- Chest pain: ECG due within 10 minutes of arrival; turns red when overdue.\n- Stroke signs: stroke alert. If blood glucose is below 70 mg/dL: \"Low blood sugar can mimic stroke - check glucose\".\n\nDeterioration alert: only when NEWS2 rises by 2 or more between two consecutive complete sets of vitals, or crosses into a higher band (5-6 medium, 7+ high). A single high reading that did not rise does not alert.\n\nNot implemented: NEWS2 SpO2 Scale 2 (for patients with chronic CO2 retention). GCS below 15 always scores 3, even if that is the patient's baseline.\n\nDemo patients are fictional. A real system would limit access by role (HIPAA).\n",
  "active_changes": [],
  "ml_sources": {
    "admission": "stub",
    "ecg": "stub",
    "xray": "stub"
  }
}
```

### GET `/metrics`

Response (200):
```json
{
  "status": "stub",
  "note": "ml/metrics.json not yet provided by Role 1"
}
```

### GET `/demo/assets`

Response (200):
```json
{
  "ecg": [
    {
      "record_id": "ptbxl_19669",
      "label": "PTB-XL record 19669"
    },
    {
      "record_id": "ptbxl_11884",
      "label": "PTB-XL record 11884"
    },
    {
      "record_id": "ptbxl_14912",
      "label": "PTB-XL record 14912"
    },
    {
      "record_id": "ptbxl_19187",
      "label": "PTB-XL record 19187"
    },
    {
      "record_id": "ptbxl_10743",
      "label": "PTB-XL record 10743"
    },
    {
      "record_id": "ptbxl_17920",
      "label": "PTB-XL record 17920"
    },
    {
      "record_id": "ptbxl_17404",
      "label": "PTB-XL record 17404"
    },
    {
      "record_id": "ptbxl_3603",
      "label": "PTB-XL record 3603"
    }
  ],
  "xray": [
    {
      "image_id": "00000842_000.png",
      "label": "NIH 00000842_000.png"
    },
    {
      "image_id": "00001039_003.png",
      "label": "NIH 00001039_003.png"
    },
    {
      "image_id": "00000591_018.png",
      "label": "NIH 00000591_018.png"
    },
    {
      "image_id": "00000459_034.png",
      "label": "NIH 00000459_034.png"
    },
    {
      "image_id": "00000468_016.png",
      "label": "NIH 00000468_016.png"
    },
    {
      "image_id": "00000579_001.png",
      "label": "NIH 00000579_001.png"
    },
    {
      "image_id": "00000773_001.png",
      "label": "NIH 00000773_001.png"
    },
    {
      "image_id": "00001158_002.png",
      "label": "NIH 00001158_002.png"
    }
  ],
  "source": "stub"
}
```

### POST `/demo/reset`

No body. Reloads the 6 seed patients with times relative to now and returns the board (same shape as `GET /board`).
