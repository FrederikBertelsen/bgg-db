using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class AlreadyExistsException : Exception, ICustomHttpException
{
    /// <summary>
    /// "{ENTITY} with {PROPERTY} '{VALUE}' already exists"
    /// </summary>
    public AlreadyExistsException(string entityName, string propertyName, object value)
        : base($"{entityName} with {propertyName} '{value}' already exists")
    { }
    public int StatusCode => 409;
}