using BGGAPI.Src.Exceptions.Interfaces;

namespace BGGAPI.Src.Exceptions;

public class InvalidValueException : Exception, ICustomHttpException
{
    /// <summary>
    /// "{PROPERTY} must be {CONSTRAINT}, but got '{ACTUAL_VALUE}'"
    /// </summary>
    public InvalidValueException(string propertyName, string constraint, object actualValue)
        : base($"{propertyName} must be {constraint}, but got '{actualValue}'")
    { }

    /// <summary>
    /// "{PROPERTY} must be {CONSTRAINT}"
    /// </summary>
    public InvalidValueException(string propertyName, string constraint)
        : base($"{propertyName} must be {constraint}")
    { }

    public int StatusCode => 400;
}