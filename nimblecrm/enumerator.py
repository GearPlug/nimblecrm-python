from enum import Enum

class ErrorEnum(Enum):
    Forbidden = 403
    Not_Found = 404
    Internal_Server_Error = 500
    Service_Unavailable = 503
    Bad_Request = 400
    Unauthorized = 401
    InvalidParameters = 409
    QuotaExceeded = 402