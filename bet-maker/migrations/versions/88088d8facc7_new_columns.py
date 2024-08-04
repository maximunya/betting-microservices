"""New columns

Revision ID: 88088d8facc7
Revises: 71a29d2b4718
Create Date: 2024-08-04 03:32:54.442259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88088d8facc7'
down_revision: Union[str, None] = '71a29d2b4718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bets', sa.Column('coefficient', sa.Numeric(precision=3, scale=2), nullable=False))
    op.add_column('bets', sa.Column('possible_winning', sa.Numeric(precision=15, scale=2), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('bets', 'possible_winning')
    op.drop_column('bets', 'coefficient')
    # ### end Alembic commands ###
