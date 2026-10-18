import pytest
from app.core.exceptions.authentication import (
    InvalidTwoFactorChallengeError,
    TwoFactorChallengeExpiredError,
)
from app.services.auth.two_factor_challenge import (
    TwoFactorChallenge,
    TwoFactorChallengeService,
)



@pytest.mark.asyncio
async def test_create_success(mock_redis):
    """
    Test successful creation of a 2FA challenge.

    Verifies that a challenge token is generated and stored in Redis.
    """
    user_id = "user_123"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    assert isinstance(token, str)

    # Verify Redis key exists and contains user_id
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)
    assert challenge.user_id == user_id


@pytest.mark.asyncio
async def test_validate_success(mock_redis):
    """
    Test successful validation of a 2FA challenge token.
    """
    user_id = "user_456"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    assert isinstance(challenge, TwoFactorChallenge)
    assert challenge.user_id == user_id
    assert challenge.challenge_id is not None


@pytest.mark.asyncio
async def test_validate_invalid_token(mock_redis):
    """
    Test that validation fails for an invalid or non-existent token.
    """
    with pytest.raises(InvalidTwoFactorChallengeError):
        await TwoFactorChallengeService.validate(mock_redis, "invalid.token.here")



@pytest.mark.asyncio
async def test_validate_expired_challenge(mock_redis):
    """
    Test that validation fails for an expired challenge.
    """
    user_id = "user_789"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    # Manually delete from Redis to simulate expiration
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)
    await mock_redis.delete(TwoFactorChallengeService._key(challenge.challenge_id))

    with pytest.raises(TwoFactorChallengeExpiredError):
        await TwoFactorChallengeService.validate(mock_redis, token)



@pytest.mark.asyncio
async def test_validate_user_mismatch(mock_redis):
    """
    Test that validation fails if the token belongs to a different user.
    """
    user_id = "user_abc"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    # Manually change the user_id in Redis to simulate a mismatch
    await mock_redis.set(
        TwoFactorChallengeService._key(challenge.challenge_id), "wrong_user"
    )

    with pytest.raises(InvalidTwoFactorChallengeError):
        await TwoFactorChallengeService.validate(mock_redis, token)



@pytest.mark.asyncio
async def test_consume_success(mock_redis):
    """
    Test successful consumption of a 2FA challenge.

    Verifies that consuming a challenge succeeds and removes the challenge from Redis.
    """
    user_id = "user_consume"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    # First consumption should succeed
    result = await TwoFactorChallengeService.consume(mock_redis, challenge)
    assert result is True

    # Verify key is gone from Redis
    exists = await mock_redis.exists(
        TwoFactorChallengeService._key(challenge.challenge_id)
    )
    assert exists == 0


@pytest.mark.asyncio
async def test_consume_already_used(mock_redis):
    """
    Test that a 2FA challenge cannot be consumed more than once.
    """
    user_id = "user_consume_twice"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    # First consumption
    await TwoFactorChallengeService.consume(mock_redis, challenge)

    # Second consumption should fail
    result = await TwoFactorChallengeService.consume(mock_redis, challenge)
    assert result is False
