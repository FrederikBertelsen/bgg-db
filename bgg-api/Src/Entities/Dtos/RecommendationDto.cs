namespace BGGAPI.Src.Entities.Dtos;

public record RecommendationDto
(
    double Score,
    BoardGameCardDto BoardGame
);