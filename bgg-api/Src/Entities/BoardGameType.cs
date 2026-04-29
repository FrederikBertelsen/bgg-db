namespace BGGAPI.Src.Entities;

public sealed class BoardGameType
{
    public int Id { get; set; }
    public required string Name { get; set; }

    public ICollection<BoardGame> BoardGames { get; set; } = new HashSet<BoardGame>();
}
