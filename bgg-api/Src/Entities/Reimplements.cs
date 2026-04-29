using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace BGGAPI.Src.Entities;

public class Reimplements
{
    [Key]
    [DatabaseGenerated(DatabaseGeneratedOption.None)]
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Url { get; set; }

    public required int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
