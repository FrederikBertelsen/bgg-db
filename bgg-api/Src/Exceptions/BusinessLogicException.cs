using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class BusinessLogicException(string message) : Exception(message.ToLower()), ICustomHttpException
{
    public int StatusCode => 400;
}