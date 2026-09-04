from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)

refresh_token_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/refresh",
)

OAuth2Token = Annotated[
    str,
    Depends(oauth2_scheme),
]

RefreshToken = Annotated[
    str,
    Depends(refresh_token_scheme),
]
