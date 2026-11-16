"""Switches for proposed safety changes. All OFF = docs/CONTRACT.md exactly as written.
Turn one on only after the team agrees (see CONTRACT_CHANGES.md)."""

# Proposed change 1: NEWS2 sets a minimum priority, so a low admission probability cannot hide an unstable patient.
NEWS2_PRIORITY_FLOOR = False
FLOOR_HIGH, FLOOR_MEDIUM, FLOOR_SINGLE_3 = 70, 50, 40  # NEWS2 >= 7, NEWS2 5-6, any single parameter = 3

# Proposed change 2: status alert on a NEWS2 7+ (or a single 3) even without a rise, per NEWS2 guidance.
NEWS2_STATUS_ALERTS = False

ECG_DUE_MIN = 10          # chest pain: ECG within 10 minutes of arrival
QUEUE_POINT_EVERY_MIN = 15  # +1 queue point per full 15 minutes waited
