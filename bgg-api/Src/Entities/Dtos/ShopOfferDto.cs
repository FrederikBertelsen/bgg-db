namespace BGGAPI.Src.Entities.Dtos;

public record ShopOfferDto
(
    string Seller,
    string Country,
    string ProductUrl,
    string ImageUrl,
    decimal PriceUSD,
    decimal PriceDKK
);