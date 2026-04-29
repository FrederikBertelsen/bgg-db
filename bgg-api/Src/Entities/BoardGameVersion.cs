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

    public double? WeightKg { get; set; }

    public double? Width { get; set; }
    public double? Depth { get; set; }
    public double? Length { get; set; }

    public int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
