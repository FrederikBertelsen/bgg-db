namespace BGGAPI.Src.Entities;

public enum PlayerCountPollRecommendation
{
    NotRecommended = 1,
    Recommended = 2,
    Best = 3,
}

public sealed class PlayerCountScore
{
    public int Id { get; set; }

    public int BoardGameId { get; set; }
    public BoardGame BoardGame { get; set; } = null!;

    public int PlayerCount { get; set; }
    public double Score { get; set; }
}