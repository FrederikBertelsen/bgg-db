namespace BGGAPI.Src.Entities;

public sealed class Recommendation
{
    public int Id { get; set; }

    public int SeedBoardGameId { get; set; }
    public BoardGame? SeedBoardGame { get; set; }

    public int RecommendedBoardGameId { get; set; }
    public BoardGame? RecommendedBoardGame { get; set; }

    public float Score { get; set; }

    public DateTimeOffset ComputedAt { get; set; }
    public string? Version { get; set; }
}
