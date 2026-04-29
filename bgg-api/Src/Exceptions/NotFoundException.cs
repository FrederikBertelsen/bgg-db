using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class NotFoundException : Exception, ICustomHttpException
{
    /// <summary>
    /// "{ENTITY} with {PROPERTY} '{VALUE}' was not found"
    /// </summary>
    public NotFoundException(string entityName, string propertyName, object value)
        : base($"{entityName} with {propertyName} '{value}' was not found")
    { }

    public int StatusCode => 404;
}