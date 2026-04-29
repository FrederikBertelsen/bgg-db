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

    public decimal? Price { get; set; }
    public decimal? PriceUSD { get; set; }
    public decimal? PriceDKK { get; set; }

    public string? ProductUrl { get; set; }

    public string? ImageUrl { get; set; }

    public int BoardGameId { get; set; }
    public BoardGame? BoardGame { get; set; }
}
