using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class ForbiddenException : Exception, ICustomHttpException
{
    /// <summary>
    /// Creates a ForbiddenException with a default message
    /// </summary>
    public ForbiddenException() : base("Access forbidden")
    { }

    /// <summary>
    /// Creates a ForbiddenException with a custom message
    /// </summary>
    public ForbiddenException(string message) : base(message)
    { }

    public int StatusCode => 403;
}