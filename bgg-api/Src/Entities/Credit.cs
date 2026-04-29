using System.ComponentModel.DataAnnotations;

namespace BGGAPI.Src.Entities;

public class Credit
{
    [Key]
    public int Id { get; set; }
    public required string Role { get; set; }
    public required string Name { get; set; }

    public int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
