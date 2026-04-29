namespace BGGAPI.Src.Entities.Dtos;

public record VersionDto
(
    string Name,
    int YearPublished,
    string? Url,
    string? ImageUrl
);