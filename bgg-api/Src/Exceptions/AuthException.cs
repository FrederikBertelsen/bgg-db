using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class AuthException(string internalMessage) : Exception("Authentication failed"), ICustomHttpException
{
    public string InternalMessage { get; init; } = internalMessage;

    public int StatusCode => 401;
}