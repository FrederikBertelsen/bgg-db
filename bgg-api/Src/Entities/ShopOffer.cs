using System.ComponentModel.DataAnnotations;
using BGGAPI.Src.Entities.Dtos;

namespace BGGAPI.Src.Entities;

public class ShopOffer
{
    [Key]
    public int Id { get; set; }


    public required string Seller { get; set; }

    public string? SellerCountry { get; set; }

    public string? Currency { get; set; }

    public float? Price { get; set; }
    public float? PriceUSD { get; set; }
    public float? PriceDKK { get; set; }

    public string? ProductUrl { get; set; }
    
    public string? ImageUrl { get; set; }

    public required int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
