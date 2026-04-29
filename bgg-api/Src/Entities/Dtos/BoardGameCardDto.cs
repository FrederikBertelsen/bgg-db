namespace BGGAPI.Src.Entities.Dtos;

public record BoardGameCardDto
(
    int Id,
    string Name,
    string ShortDescription,
    int YearPublished,
    float AverageRating,
    float AverageWeight,
    RankDto[] Ranks,
    int MinPlayers,
    int MaxPlayers,
    int MinPlaytimeMinutes,
    int MaxPlaytimeMinutes,
    string? ThumbnailUrl
);