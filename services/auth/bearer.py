
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import decode_jwt

# the JWTBearer class is a subclass of FastAPI's HTTPBearer class that will be used to persist authentication on our routes
class JWTBearer(HTTPBearer):
    # we enabled automatic error reporting by setting the boolean auto_error to True
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    # we defined a variable called credentials of type HTTPAuthorizationCredentials, 
    # which is created when the JWTBearer class is invoked. 
    # We then proceeded to check if the credentials passed in during the course of invoking the class are valid:
    # If the credential scheme isn't a bearer scheme, we raised an exception for an invalid token scheme.
    # If a bearer token was passed, we verified that the JWT is valid.
    # If no credentials were received, we raised an invalid authorization error.
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
        
    # The verify_jwt method verifies whether a token is valid. 
    # The method takes a jwtoken string which it then passes to the decode_jwt function and returns a boolean value based on the outcome from decode_jwt
    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        payload = decode_jwt(jwtoken) # decode_jwt now returns None on error or expiration
        if payload:
            isTokenValid = True

        return isTokenValid