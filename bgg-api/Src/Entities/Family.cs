namespace BGGAPI.Src.Entities;

public sealed class Family
{
    public int Id { get; set; }
    public required string Name { get; set; }

    public ICollection<BoardGame> BoardGameCategories { get; set; } = new HashSet<BoardGame>();
}
