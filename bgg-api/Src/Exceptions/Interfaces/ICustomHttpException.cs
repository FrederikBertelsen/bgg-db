namespace BGGAPI.Src.Exceptions.Interfaces;

public interface ICustomHttpException
{
    int StatusCode { get; }
}