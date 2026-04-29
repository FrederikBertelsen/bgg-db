using System.ComponentModel.DataAnnotations;

namespace BGGAPI.Src.Entities;

public class BoardGameVersion
{
    [Key]
    public int Id { get; set; }

    public required string Name { get; set; }
    public int YearPublished { get; set; }
    public string? Url { get; set; }
    public string? ImageUrl { get; set; }

    public float? WeightKg { get; set; }

    public float? Width { get; set; }
    public float? Depth { get; set; }
    public float? Length { get; set; }

    public required int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
