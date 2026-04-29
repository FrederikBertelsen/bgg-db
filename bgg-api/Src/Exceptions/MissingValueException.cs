using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class MissingValueException : Exception, ICustomHttpException
{
    /// <summary>
    /// "{PROPERTY} is required for {ENTITY}"
    /// </summary>
    public MissingValueException(string entityName, string propertyName)
        : base($"{propertyName} is required for {entityName}")
    { }

    /// <summary>
    /// "{VALUE_NAME} is required"
    /// </summary>
    public MissingValueException(string valueName)
    : base($"{valueName} is required")
    { }
    public int StatusCode => 400;
}