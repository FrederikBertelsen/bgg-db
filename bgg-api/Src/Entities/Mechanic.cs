namespace BGGAPI.Src.Entities;

public sealed class Mechanic
{
    public int Id { get; set; }
    public required string Name { get; set; }

    public int DocumentFrequency { get; set; }
    public double Idf { get; set; }
    public double Weight { get; set; }

    public ICollection<BoardGame> BoardGames { get; set; } = new HashSet<BoardGame>();
}
