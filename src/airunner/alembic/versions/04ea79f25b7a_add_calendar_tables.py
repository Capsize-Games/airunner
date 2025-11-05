"""add calendar tables

Revision ID: 04ea79f25b7a
Revises: 91e21ecaef23
Create Date: 2025-10-27 14:38:11.893120

"""

from typing import Sequence, Union

from airunner.components.calendar.data.event import Event
from airunner.components.calendar.data.reminder import Reminder
from airunner.components.calendar.data.recurring_event import RecurringEvent
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "04ea79f25b7a"
down_revision: Union[str, None] = "91e21ecaef23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create calendar tables
    add_table(RecurringEvent)  # Create first since Event references it
    add_table(Event)
    add_table(Reminder)  # Create last since it references Event


def downgrade() -> None:
    # Drop in reverse order
    drop_table(Reminder)
    drop_table(Event)
    drop_table(RecurringEvent)
