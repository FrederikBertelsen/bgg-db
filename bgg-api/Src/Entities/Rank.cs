using System.ComponentModel.DataAnnotations;

namespace BGGAPI.Src.Entities;

public class Rank
{
    [Key]
    public int Id { get; set; }
    public required string Category { get; set; }

    public int Placement { get; set; }

    public float? BayesAverage { get; set; }

    public required int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }

}
