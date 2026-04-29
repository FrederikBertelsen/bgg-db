namespace BGGAPI.Src.Entities;

public sealed class Category
{
    public int Id { get; set; }
    public required string Name { get; set; }

    public ICollection<BoardGame> BoardGameCategories { get; set; } = new HashSet<BoardGame>();
}
