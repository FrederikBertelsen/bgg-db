namespace BGGAPI.Src.Entities;

public sealed class AlternativeName
{
    public int Id { get; set; }
    public required string Name { get; set; }

    public required int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
