namespace BGGAPI.Src.Entities.Dtos;

public record RecommendationDto
(
    float Score,
    BoardGameCardDto BoardGame
);