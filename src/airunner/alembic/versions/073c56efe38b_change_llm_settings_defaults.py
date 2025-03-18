"""change llm settings defaults

Revision ID: 073c56efe38b
Revises: bbd45baafc6f
Create Date: 2025-03-18 14:29:00.483534

"""
from typing import Sequence, Union

from airunner.data.models import LLMGeneratorSettings
from airunner.utils.db import set_default


# revision identifiers, used by Alembic.
revision: str = '073c56efe38b'
down_revision: Union[str, None] = 'bbd45baafc6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    set_default(LLMGeneratorSettings, "do_sample", False)
    set_default(LLMGeneratorSettings, "ngram_size", 0)
    set_default(LLMGeneratorSettings, "length_penalty", 900)


def downgrade() -> None:
    set_default(LLMGeneratorSettings, "do_sample", True)
    set_default(LLMGeneratorSettings, "ngram_size", 2)
    set_default(LLMGeneratorSettings, "length_penalty", 100)