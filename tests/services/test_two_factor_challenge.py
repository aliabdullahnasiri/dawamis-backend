import pytest

from app.services.auth.two_factor_challenge import (
    TwoFactorChallenge,
    TwoFactorChallengeService,
)


@pytest.mark.asyncio
async def test_create_success(mock_redis):
    user_id = "user_123"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    assert isinstance(token, str)

    # Verify Redis key exists and contains user_id
    # We need to extract challenge_id from token to check key,
    # but we can also just validate it.
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)
    assert challenge.user_id == user_id


@pytest.mark.asyncio
async def test_validate_success(mock_redis):
    user_id = "user_456"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    assert isinstance(challenge, TwoFactorChallenge)
    assert challenge.user_id == user_id
    assert challenge.challenge_id is not None


@pytest.mark.asyncio
async def test_validate_invalid_token(mock_redis):
    with pytest.raises(ValueError, match="auth:invalid_two_factor_challenge"):
        await TwoFactorChallengeService.validate(mock_redis, "invalid.token.here")


@pytest.mark.asyncio
async def test_validate_expired_challenge(mock_redis):
    user_id = "user_789"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    # Manually delete from Redis to simulate expiration
    # We need the challenge_id. We can get it by validating first.
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)
    await mock_redis.delete(TwoFactorChallengeService._key(challenge.challenge_id))

    with pytest.raises(ValueError, match="auth:two_factor_challenge_expired"):
        await TwoFactorChallengeService.validate(mock_redis, token)


@pytest.mark.asyncio
async def test_validate_user_mismatch(mock_redis):
    user_id = "user_abc"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)

    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    # Manually change the user_id in Redis to simulate a mismatch
    await mock_redis.set(
        TwoFactorChallengeService._key(challenge.challenge_id), "wrong_user"
    )

    with pytest.raises(ValueError, match="auth:invalid_two_factor_challenge"):
        await TwoFactorChallengeService.validate(mock_redis, token)


@pytest.mark.asyncio
async def test_consume_success(mock_redis):
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
    user_id = "user_consume_twice"
    token = await TwoFactorChallengeService.create(mock_redis, user_id)
    challenge = await TwoFactorChallengeService.validate(mock_redis, token)

    # First consumption
    await TwoFactorChallengeService.consume(mock_redis, challenge)

    # Second consumption should fail
    result = await TwoFactorChallengeService.consume(mock_redis, challenge)
    assert result is False
