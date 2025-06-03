"""update bootstrap data

Revision ID: 449cbcdca2c4
Revises: f54532589efa
Create Date: 2025-05-10 05:41:39.672153

"""

from typing import Sequence, Union
from airunner.data.models.image_filter import ImageFilter
from airunner.data.models.image_filter_value import ImageFilterValue
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "449cbcdca2c4"
down_revision: Union[str, None] = "f54532589efa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

color_balance_data = {
    "cyan_red": {
        "name": "cyan_red",
        "value": "0.0",
        "value_type": "float",
        "min_value": None,
        "max_value": None,
    },
    "magenta_green": {
        "name": "magenta_green",
        "value": "0.0",
        "value_type": "float",
        "min_value": None,
        "max_value": None,
    },
    "yellow_blue": {
        "name": "yellow_blue",
        "value": "0.0",
        "value_type": "float",
        "min_value": None,
        "max_value": None,
    },
}


def upgrade() -> None:
    image_filter_values = color_balance_data
    image_filter_values["cyan_red"]["min_value"] = -1.0
    image_filter_values["cyan_red"]["max_value"] = 1.0

    image_filter_values["magenta_green"]["min_value"] = -1.0
    image_filter_values["magenta_green"]["max_value"] = 1.0

    image_filter_values["yellow_blue"]["min_value"] = -1.0
    image_filter_values["yellow_blue"]["max_value"] = 1.0

    for k, v in image_filter_values.items():
        item = ImageFilterValue.objects.first(ImageFilter.name == k)
        if not item:
            return
        ImageFilterValue.objects.update(
            item.id,
            value=v["value"],
            value_type=v["value_type"],
            min_value=v["min_value"],
            max_value=v["max_value"],
        )


def downgrade() -> None:
    image_filter = ImageFilter.objects.first(ImageFilter.name == "color_balance")
    if not image_filter:
        return
    ImageFilter.objects.update(image_filter.id, image_filter_values=color_balance_data)
