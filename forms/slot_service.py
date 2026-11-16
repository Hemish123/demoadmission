"""
Service for auto-allocating interaction time slots as per Shreyas Foundation Chart:
- Scheduled Range: November 26 – December 8 (10-11 working days)
- Capacity: 30–40 families daily
- 4 Slots per day (10 children per slot):
  * Slot 1: 9:00 AM TO 10:00 AM
  * Slot 2: 10:00 AM TO 11:00 AM
  * Slot 3: 11:00 AM TO 12:00 PM
  * Slot 4: 12:00 PM TO 1:00 PM
- Schedule Days: Monday to Saturday (Sundays skipped)
- First-come, first-served
"""
import logging
from datetime import date, timedelta
from django.utils import timezone
from .models import AdmissionApplication

logger = logging.getLogger(__name__)

INTERACTION_START_DATE = date(2026, 11, 26)
INTERACTION_END_DATE = date(2026, 12, 8)

SLOT_DEFINITIONS = [
    {"slot_no": 1, "time": "9:00 AM TO 10:00 AM", "capacity": 10},
    {"slot_no": 2, "time": "10:00 AM TO 11:00 AM", "capacity": 10},
    {"slot_no": 3, "time": "11:00 AM TO 12:00 PM", "capacity": 10},
    {"slot_no": 4, "time": "12:00 PM TO 1:00 PM", "capacity": 10},
]


def allocate_next_available_interaction_slot(reference_date=None) -> dict:
    """
    Finds the earliest available interaction slot strictly in the Official Interaction Window:
    - Scheduled Range: November 26, 2026 – December 8, 2026 (Working days Mon-Sat)
    - Capacity: 30–40 families daily across 4 hourly slots (10 children/slot):
        * Slot 1: 9:00 AM TO 10:00 AM
        * Slot 2: 10:00 AM TO 11:00 AM
        * Slot 3: 11:00 AM TO 12:00 PM
        * Slot 4: 12:00 PM TO 1:00 PM
    - Sundays are skipped automatically.
    - First-come, first-served allocation on admission form completion.
    - Dispatches WhatsApp notification immediately upon submission.
    """
    current_date = reference_date or INTERACTION_START_DATE

    # Search through the interaction window (Nov 26 to Dec 8)
    while current_date <= (INTERACTION_END_DATE or date(2026, 12, 31)):
        # Skip Sundays
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue

        for slot_def in SLOT_DEFINITIONS:
            slot_no = slot_def["slot_no"]
            slot_time = slot_def["time"]
            capacity = slot_def["capacity"]

            # Count existing applications already booked for this date and slot
            booked_count = AdmissionApplication.objects.filter(
                interaction_date=current_date,
                interaction_slot_no=slot_no
            ).exclude(admission_status__in=['CANCELLED', 'REJECTED']).count()

            if booked_count < capacity:
                logger.info(
                    f"[SLOT ALLOCATED] Date: {current_date}, Slot: {slot_no} ({slot_time}), "
                    f"Position: {booked_count + 1}/{capacity}"
                )
                return {
                    "date": current_date,
                    "date_str": current_date.strftime("%d-%m-%Y"),
                    "slot_no": slot_no,
                    "time": slot_time,
                    "venue": "Shreyas Foundation – Main Office",
                    "position": booked_count + 1
                }

        # All 4 slots on current_date are full (40 kids booked) -> move to next working day
        current_date += timedelta(days=1)

    raise RuntimeError("All interaction slots for November 26 – December 8 are full.")

