from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.revoked_token import RevokedToken


@pytest.mark.asyncio
async def test_revoked_token_creation(db_session: AsyncSession):
    """
    Test basic RevokedToken model creation.
    """
    jti = str(uuid4())
    token = RevokedToken(jti=jti)
    db_session.add(token)
    await db_session.commit()

    assert token.id is not None
    assert token.jti == jti

@pytest.mark.asyncio
async def test_revoked_token_unique_jti(db_session: AsyncSession):
    """
    Test that JTI must be unique.
    """
    jti = "fixed-uuid-123"
    token1 = RevokedToken(jti=jti)
    db_session.add(token1)
    await db_session.commit()

    token2 = RevokedToken(jti=jti)
    db_session.add(token2)
    
    with pytest.raises(Exception): # SQLAlchemy IntegrityError
        await db_session.commit()
