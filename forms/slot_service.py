"""
Service for auto-allocating interaction time slots as per Shreyas Foundation Chart:
- 4 Slots per day
  * Slot 1: 9:00 AM TO 10:00 AM (10 children max)
  * Slot 2: 10:00 AM TO 11:00 AM (10 children max)
  * Slot 3: 11:00 AM TO 12:00 PM (10 children max)
  * Slot 4: 12:00 PM TO 1:00 PM (10 children max)
- Maximum 40 children per day
- Schedule Days: Monday to Saturday (Sundays skipped)
- Starting Date: Next working day after form submission date
"""
import logging
from datetime import timedelta
from django.utils import timezone
from .models import AdmissionApplication

logger = logging.getLogger(__name__)

SLOT_DEFINITIONS = [
    {"slot_no": 1, "time": "9:00 AM TO 10:00 AM", "capacity": 10},
    {"slot_no": 2, "time": "10:00 AM TO 11:00 AM", "capacity": 10},
    {"slot_no": 3, "time": "11:00 AM TO 12:00 PM", "capacity": 10},
    {"slot_no": 4, "time": "12:00 PM TO 1:00 PM", "capacity": 10},
]


def get_next_working_day(target_date):
    """
    Returns the next valid day from Monday to Saturday.
    Sunday (weekday == 6) is skipped.
    """
    candidate = target_date + timedelta(days=1)
    while candidate.weekday() == 6:  # 6 is Sunday
        candidate += timedelta(days=1)
    return candidate


def allocate_next_available_interaction_slot(reference_date=None) -> dict:
    """
    Finds the earliest available interaction slot starting from tomorrow (Mon-Sat):
    Checks each day's Slot 1 -> Slot 2 -> Slot 3 -> Slot 4.
    If a slot has < 10 children, allocates that slot.
    If all 4 slots on that day are full (40 children), rolls over to the next working day.
    """
    if not reference_date:
        reference_date = timezone.now().date()

    current_date = get_next_working_day(reference_date)

    # Search up to 60 working days ahead
    for _ in range(60):
        # Double check: skip Sunday
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
            ).count()

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
        current_date = get_next_working_day(current_date)

    raise RuntimeError("No available interaction slot found within 60 days.")

